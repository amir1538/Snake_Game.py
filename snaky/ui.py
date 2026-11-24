"""Snaky Game — HD Supersampled Native Pygame UI (2x SSAA Cards/Buttons + 3x SSAA Icons)."""

import math
from typing import Dict, List, Optional, Tuple

import pygame

from . import constants as C
from . import icons as I


def format_timer(ms: float) -> str:
    total_sec = int(ms // 1000)
    mins = total_sec // 60
    secs = total_sec % 60
    tenths = int((ms % 1000) // 100)
    return f"{mins:02d}:{secs:02d}.{tenths}"


class UIController:
    """Handles layout geometry, HD supersampled UI drawing, hover states, and mouse interactions."""

    TOP_BAR_H = 60
    PAUSE_BAR_H = 74
    BOARD_PAD = 16
    CARD_W = 300
    CARD_H = 366
    ACTION_GAP = 12
    ACTION_H = 64
    SLOT_W = 40
    ROW_H = 41
    SETTINGS_HDR_H = 38

    def __init__(self, engine, settings_manager, audio_manager, renderer) -> None:
        self.engine = engine
        self.settings_manager = settings_manager
        self.audio = audio_manager
        self.renderer = renderer

        self.is_settings_open = False
        self.state_before_settings: Optional[str] = None
        self.blender_open = False
        self.hover_label = ""
        self.is_fullscreen = False

        # Smooth horizontal carousel offsets (8 rows)
        self.row_offsets: List[float] = [0.0] * 8
        self._offsets_initialized = False

        # Cached 2x-supersampled Main Menu Card surface
        self._menu_card_cache: Optional[pygame.Surface] = None
        self._menu_card_key: Tuple = ()

        # Crisp native fonts (also 2x fonts for supersampled card rendering)
        self.font_hud = pygame.font.SysFont("segoeui,arial,sans", 24, bold=True)
        self.font_timer = pygame.font.SysFont("consolas,segoeui,monospace", 17, bold=True)
        self.font_badge = pygame.font.SysFont("segoeui,arial,sans", 13, bold=True)
        self.font_card_num_2x = pygame.font.SysFont("segoeui,arial,sans", 56, bold=True)
        self.font_win_2x = pygame.font.SysFont("segoeui,arial,sans", 36, bold=True)
        self.font_btn = pygame.font.SysFont("segoeui,arial,sans", 21, bold=True)
        self.font_pause = pygame.font.SysFont("segoeui,arial,sans", 28, bold=True)
        self.font_small = pygame.font.SysFont("segoeui,arial,sans", 13, bold=True)

        self.rects: Dict[str, pygame.Rect] = {}
        self.carousel_item_rects: List[Tuple[pygame.Rect, int, str, str]] = []
        self.carousel_row_rects: List[Tuple[pygame.Rect, int]] = []
        self.blender_tile_rects: List[Tuple[pygame.Rect, str]] = []

        self.board_origin = (0, self.TOP_BAR_H)

    # ------------------------------------------------------------------
    # Viewport & Board Sizing
    # ------------------------------------------------------------------
    def update_layout(self, win_w: int, win_h: int) -> None:
        is_paused = (self.engine.state == "PAUSED") and (not self.is_settings_open)
        pause_h = self.PAUSE_BAR_H if is_paused else 0

        avail_w = max(160, win_w - self.BOARD_PAD * 2)
        avail_h = max(140, win_h - self.TOP_BAR_H - pause_h - self.BOARD_PAD * 2)

        cell_w = avail_w // self.engine.cols
        cell_h = avail_h // self.engine.rows
        best_cell = max(12, min(cell_w, cell_h))

        if best_cell != self.engine.cell_size:
            self.engine.set_cell_size(best_cell)
            self.renderer.invalidate_cache()

        board_w = self.engine.cols * self.engine.cell_size
        board_h = self.engine.rows * self.engine.cell_size
        bx = (win_w - board_w) // 2
        by = self.TOP_BAR_H + (win_h - self.TOP_BAR_H - pause_h - board_h) // 2
        self.board_origin = (bx, by)

        cy = self.TOP_BAR_H // 2
        self.rects["btn_settings"] = pygame.Rect(win_w - 56, cy - 20, 40, 40)
        self.rects["btn_mute"] = pygame.Rect(win_w - 108, cy - 20, 40, 40)
        self.rects["btn_fullscreen"] = pygame.Rect(win_w - 160, cy - 20, 40, 40)

        if is_paused:
            bar_y = win_h - self.PAUSE_BAR_H
            self.rects["pause_bar"] = pygame.Rect(0, bar_y, win_w, self.PAUSE_BAR_H)
            self.rects["btn_continue"] = pygame.Rect((win_w - 220) // 2, bar_y + 12, 220, 50)
        else:
            self.rects.pop("btn_continue", None)

        stack_h = self.CARD_H + self.ACTION_GAP + self.ACTION_H
        sx = (win_w - self.CARD_W) // 2
        sy = max(8, (win_h - stack_h) // 2)
        self.rects["card"] = pygame.Rect(sx, sy, self.CARD_W, self.CARD_H)
        action_y = sy + self.CARD_H + self.ACTION_GAP
        self.rects["btn_play"] = pygame.Rect(sx, action_y, 224, self.ACTION_H)
        self.rects["btn_side"] = pygame.Rect(sx + 224 + self.ACTION_GAP, action_y, 64, self.ACTION_H)
        self.rects["settings_back"] = pygame.Rect(sx + 6, sy + 2, 34, 34)
        self.rects["blender_box"] = pygame.Rect(sx + 8, sy + self.CARD_H - 96, self.CARD_W - 16, 88)
        self.rects["blender_close"] = pygame.Rect(self.rects["blender_box"].right - 26, self.rects["blender_box"].top + 4, 22, 22)

    # ------------------------------------------------------------------
    # Settings Actions
    # ------------------------------------------------------------------
    def _apply_setting(self, requires_reset: bool, **patch) -> None:
        self.settings_manager.update(**patch)
        self._menu_card_key = ()
        if requires_reset:
            self.engine.apply_settings_and_reset(self.state_before_settings == "MENU")
            self.renderer.invalidate_cache()
        else:
            self.engine.settings = self.settings_manager.get()
            self.renderer.invalidate_cache()

    def open_settings(self) -> None:
        self.audio.play_click()
        if self.engine.state == "PLAYING":
            self.state_before_settings = "PLAYING"
            self.engine.state_before_pause = "PLAYING"
            self.engine.state = "PAUSED"
        else:
            self.state_before_settings = self.engine.state
        self.is_settings_open = True
        self.blender_open = (self.settings_manager.get()["mode"] == "blender")
        self._offsets_initialized = False

    def close_settings(self, start_playing: bool = False) -> None:
        self.audio.play_click()
        self.is_settings_open = False
        self.blender_open = False
        if start_playing:
            if self.engine.state == "MENU":
                self.engine.start_from_menu()
            elif self.engine.state in ("GAMEOVER", "WON"):
                self.engine.reset(show_menu=False)
            elif self.engine.state == "PAUSED":
                self.engine.resume()

    def _get_rows_spec(self, s: Dict):
        return [
            (
                s["food_type"],
                [(fid, C.FOOD_TYPES[fid]["label"]) for fid in C.FOOD_TYPE_ORDER],
                lambda val: self._apply_setting(True, food_type=val),
            ),
            (
                s["mode"],
                [(m["id"], m["name"]) for m in C.MODES],
                lambda val: (
                    setattr(self, "blender_open", val == "blender"),
                    self._apply_setting(True, mode=val),
                ),
            ),
            (
                s["food_count"],
                [(cid, f"Fruits: {C.FOOD_COUNTS[cid]['label']}") for cid in C.FOOD_COUNT_ORDER],
                lambda val: self._apply_setting(True, food_count=val),
            ),
            (
                s["speed"],
                [(sid, f"Speed: {C.SPEEDS[sid]['label']}") for sid in C.SPEED_ORDER],
                lambda val: self._apply_setting(True, speed=val),
            ),
            (
                s["board_size"],
                [(bid, C.BOARD_SIZES[bid]["label"]) for bid in C.BOARD_SIZE_ORDER],
                lambda val: self._apply_setting(True, board_size=val),
            ),
            (
                s["snake_color"],
                [(cid, f"Color: {C.SNAKE_COLORS[cid]['label']}") for cid in C.SNAKE_COLOR_ORDER],
                lambda val: self._apply_setting(False, snake_color=val),
            ),
            (
                s["theme"],
                [(tid, f"Theme: {C.THEMES[tid]['label']}") for tid in C.THEME_ORDER],
                lambda val: self._apply_setting(False, theme=val),
            ),
            (
                s["graphics_style"],
                [(gid, f"Graphics: {C.GRAPHICS_STYLES[gid]['label']}") for gid in C.GRAPHICS_STYLE_ORDER],
                lambda val: self._apply_setting(False, graphics_style=val),
            ),
        ]

    # ------------------------------------------------------------------
    # Mouse Input Handling
    # ------------------------------------------------------------------
    def handle_mouse_down(self, pos: Tuple[int, int], button: int, on_toggle_fullscreen) -> bool:
        if button != 1:
            return False

        if self.is_settings_open:
            if self.blender_open and self.settings_manager.get()["mode"] == "blender":
                if self.rects["blender_close"].collidepoint(pos):
                    self.audio.play_click()
                    self.blender_open = False
                    return True
                for rect, mid in self.blender_tile_rects:
                    if rect.collidepoint(pos):
                        self.audio.play_click()
                        bm = self.settings_manager.get()["blender_modes"]
                        if mid in bm:
                            if len(bm) <= 2:
                                return True
                            bm = [m for m in bm if m != mid]
                        else:
                            bm.append(mid)
                        self._apply_setting(True, blender_modes=bm)
                        return True
                if self.rects["blender_box"].collidepoint(pos):
                    return True

            if self.rects["settings_back"].collidepoint(pos):
                self.close_settings(start_playing=False)
                return True
            if self.rects["btn_play"].collidepoint(pos):
                self.close_settings(start_playing=True)
                return True
            if self.rects["btn_side"].collidepoint(pos):
                self.audio.play_click()
                self.settings_manager.randomize()
                self._menu_card_key = ()
                self.engine.apply_settings_and_reset(self.state_before_settings == "MENU")
                self.renderer.invalidate_cache()
                self.blender_open = (self.settings_manager.get()["mode"] == "blender")
                return True

            rows_spec = self._get_rows_spec(self.settings_manager.get())
            for rect, row_idx, item_id, _ in self.carousel_item_rects:
                if rect.collidepoint(pos):
                    self.audio.play_click()
                    rows_spec[row_idx][2](item_id)
                    return True

            if not self.rects["card"].collidepoint(pos) and not self.rects["btn_play"].collidepoint(pos) and not self.rects["btn_side"].collidepoint(pos):
                self.close_settings(start_playing=False)
                return True
            return True

        if self.rects["btn_mute"].collidepoint(pos):
            next_muted = not self.settings_manager.get()["muted"]
            self.settings_manager.update(muted=next_muted)
            self.audio.set_muted(next_muted)
            if not next_muted:
                self.audio.play_click()
            return True
        if self.rects["btn_settings"].collidepoint(pos):
            self.open_settings()
            return True
        if self.rects["btn_fullscreen"].collidepoint(pos):
            self.audio.play_click()
            on_toggle_fullscreen()
            return True

        if self.engine.state == "PAUSED" and "btn_continue" in self.rects:
            if self.rects["btn_continue"].collidepoint(pos):
                self.engine.resume()
                return True

        if self.engine.state in ("MENU", "GAMEOVER", "WON"):
            if self.rects["btn_play"].collidepoint(pos):
                self.audio.play_click()
                if self.engine.state == "MENU":
                    self.engine.start_from_menu()
                else:
                    self.engine.reset(show_menu=False)
                return True
            if self.rects["btn_side"].collidepoint(pos):
                self.open_settings()
                return True

        return False

    def handle_mouse_wheel(self, pos: Tuple[int, int], wheel_y: int) -> bool:
        if not self.is_settings_open:
            return False
        s = self.settings_manager.get()
        rows_spec = self._get_rows_spec(s)
        for rect, row_idx in self.carousel_row_rects:
            if rect.collidepoint(pos):
                cur_val, items, on_sel = rows_spec[row_idx]
                ids = [it[0] for it in items]
                cur_idx = ids.index(cur_val) if cur_val in ids else 0
                delta = -1 if wheel_y > 0 else 1
                next_idx = max(0, min(len(ids) - 1, cur_idx + delta))
                if next_idx != cur_idx:
                    self.audio.play_click()
                    on_sel(ids[next_idx])
                return True
        return False

    # ------------------------------------------------------------------
    # HD Supersampled Rendering
    # ------------------------------------------------------------------
    def _draw_top_bar(self, screen: pygame.Surface, theme: Dict, mouse_pos: Tuple[int, int]) -> None:
        win_w = screen.get_width()
        s = self.settings_manager.get()
        pygame.draw.rect(screen, theme["top_bar"], (0, 0, win_w, self.TOP_BAR_H))

        cy = self.TOP_BAR_H // 2
        I.draw_fruit(screen, s["food_type"], 36, cy, 30, 0.95, theme["shadow"], False, 255, False, 0.0, False)
        sc_txt = self.font_hud.render(str(self.engine.score), True, C.UI_WHITE)
        screen.blit(sc_txt, sc_txt.get_rect(midleft=(58, cy)))

        I.draw_trophy(screen, 134, cy + 1, scale=0.80)
        hi_txt = self.font_hud.render(str(self.engine.high_score), True, C.UI_WHITE)
        screen.blit(hi_txt, hi_txt.get_rect(midleft=(158, cy)))

        if s["show_timer"]:
            t_str = format_timer(self.engine.elapsed_ms)
            t_surf = self.font_timer.render(t_str, True, C.UI_WHITE)
            pill = pygame.Rect(228, cy - 15, t_surf.get_width() + 20, 30)
            I.draw_rounded_rect_aa(screen, (0, 0, 0, 56), pill, 6)
            screen.blit(t_surf, t_surf.get_rect(center=pill.center))

        if s["mode"] != "classic":
            badge_str = (
                f"Blender ({len(s['blender_modes'])})"
                if s["mode"] == "blender"
                else C.MODE_MAP.get(s["mode"], {}).get("name", "Classic")
            )
            b_surf = self.font_badge.render(badge_str, True, C.UI_WHITE)
            bw = b_surf.get_width() + 22
            bx = self.rects["btn_fullscreen"].left - bw - 12
            I.draw_rounded_rect_aa(screen, (255, 255, 255, 42), pygame.Rect(bx, cy - 13, bw, 26), 13)
            screen.blit(b_surf, b_surf.get_rect(center=(bx + bw // 2, cy)))

        for key in ("btn_fullscreen", "btn_mute", "btn_settings"):
            r = self.rects[key]
            if r.collidepoint(mouse_pos):
                I.draw_rounded_rect_aa(screen, (255, 255, 255, 42), r, r.width // 2)

        I.draw_fullscreen_icon(screen, self.rects["btn_fullscreen"].centerx, self.rects["btn_fullscreen"].centery, self.is_fullscreen)
        I.draw_speaker_icon(screen, self.rects["btn_mute"].centerx, self.rects["btn_mute"].centery, s["muted"])
        I.draw_gear_icon(screen, self.rects["btn_settings"].centerx, self.rects["btn_settings"].centery, radius=9, hole_color=theme["top_bar"])

    def _draw_pause_ui(self, screen: pygame.Surface, theme: Dict, mouse_pos: Tuple[int, int]) -> None:
        win_w, _ = screen.get_size()
        bar_rect = self.rects["pause_bar"]

        ov = pygame.Surface((win_w, bar_rect.top - self.TOP_BAR_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 115))
        screen.blit(ov, (0, self.TOP_BAR_H))

        p_txt = self.font_pause.render("PAUSED", True, C.UI_WHITE)
        pw, ph = p_txt.get_width() + 56, 54
        px = (win_w - pw) // 2
        py = self.TOP_BAR_H + (bar_rect.top - self.TOP_BAR_H - ph) // 2
        I.draw_rounded_rect_aa(screen, (0, 0, 0, 175), pygame.Rect(px, py, pw, ph), 8)
        screen.blit(p_txt, p_txt.get_rect(center=(px + pw // 2, py + ph // 2)))

        pygame.draw.rect(screen, theme["top_bar"], bar_rect)
        btn = self.rects["btn_continue"]
        col = C.UI_BTN_BLUE_HOVER if btn.collidepoint(mouse_pos) else C.UI_BTN_BLUE
        I.draw_rounded_rect_aa(screen, col, btn, 8)
        c_txt = self.font_btn.render("Continue", True, C.UI_WHITE)
        total_w = 24 + c_txt.get_width()
        start_x = btn.centerx - total_w // 2
        I.draw_play_triangle(screen, start_x + 7, btn.centery, size=8)
        screen.blit(c_txt, c_txt.get_rect(midleft=(start_x + 24, btn.centery)))

    def _build_main_menu_card_2x(self, theme: Dict, s: Dict) -> pygame.Surface:
        """Builds a 2x-supersampled (600x732 -> 300x366) razor-sharp Main Menu card."""
        cw, ch = self.CARD_W, self.CARD_H
        sc = 2
        hi_w, hi_h = cw * sc, ch * sc
        card = pygame.Surface((hi_w, hi_h), pygame.SRCALPHA)
        card.fill((*theme["card_sky"], 255))

        # 3-row 26x26px checkered grass strip
        grass_top = 289 * sc
        tile = 26 * sc
        for r in range(3):
            for c in range(12):
                gcol = theme["grass_light"] if (r + c) % 2 == 0 else theme["grass_dark"]
                pygame.draw.rect(card, gcol, (c * tile, grass_top + r * tile, tile, tile))

        if self.engine.state == "WON":
            w_txt = self.font_win_2x.render("YOU WIN!", True, C.UI_WHITE)
            card.blit(w_txt, w_txt.get_rect(center=(hi_w // 2, 30 * sc)))

        # Crisp 2x Apple/Fruit & Gold Trophy + Scores
        I.draw_fruit(card, s["food_type"], 85 * sc, 108 * sc, 56 * sc, 1.0, theme["shadow"], False, 255, False, 0.0, False)
        s_txt = self.font_card_num_2x.render(str(self.engine.score), True, C.UI_WHITE)
        card.blit(s_txt, s_txt.get_rect(center=(85 * sc, 162 * sc)))

        I.draw_trophy(card, 215 * sc, 108 * sc, scale=1.65 * sc)
        h_txt = self.font_card_num_2x.render(str(self.engine.high_score), True, C.UI_WHITE)
        card.blit(h_txt, h_txt.get_rect(center=(215 * sc, 162 * sc)))

        # Silky-smooth 2x Smiling Snake sitting flush on grass
        color_cfg = C.SNAKE_COLORS.get(s["snake_color"], C.SNAKE_COLORS["blue"])
        sn_fill = color_cfg["head"]
        sn_dark = color_cfg["pupil"]
        sy = grass_top - 36 * sc
        pygame.draw.rect(card, sn_fill, (0, sy + 2 * sc, 194 * sc, 34 * sc))
        pygame.draw.circle(card, sn_fill, (194 * sc, sy + 19 * sc), 17 * sc)
        pygame.draw.ellipse(card, sn_fill, (124 * sc, sy - 6 * sc, 76 * sc, 28 * sc))

        e1x, e2x, ey = 137 * sc, 155 * sc, sy - 6 * sc
        pygame.draw.circle(card, sn_fill, (e1x, ey), 11 * sc)
        pygame.draw.circle(card, sn_fill, (e2x, ey), 11 * sc)
        for ex in (e1x, e2x):
            pygame.draw.circle(card, C.UI_WHITE, (ex, ey), 7 * sc)
            pygame.draw.circle(card, sn_dark, (ex - 2 * sc, ey - 1 * sc), 4 * sc)
            pygame.draw.circle(card, C.UI_WHITE, (ex - 3 * sc, ey - 2 * sc), max(1, int(1.3 * sc)))

        pygame.draw.ellipse(card, sn_dark, (196 * sc, sy + 5 * sc, 3 * sc, 6 * sc))
        pygame.draw.ellipse(card, sn_dark, (203 * sc, sy + 5 * sc, 3 * sc, 6 * sc))

        mouth_y = sy + 18 * sc
        pygame.draw.line(card, sn_dark, (133 * sc, mouth_y), (210 * sc, mouth_y), 2 * sc)
        pygame.draw.arc(card, sn_dark, (126 * sc, mouth_y - 7 * sc, 12 * sc, 10 * sc), math.pi, 1.85 * math.pi, 2 * sc)

        # Clip to razor-sharp rounded corners at 2x with white-RGB transparent mask (zero corner halo!)
        mask = pygame.Surface((hi_w, hi_h), pygame.SRCALPHA)
        mask.fill((255, 255, 255, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, hi_w, hi_h), border_radius=8 * sc)
        card.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return pygame.transform.smoothscale(card, (cw, ch))

    def _draw_main_menu_modal(self, screen: pygame.Surface, theme: Dict, mouse_pos: Tuple[int, int]) -> None:
        win_w, win_h = screen.get_size()
        s = self.settings_manager.get()

        ov = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 178))
        screen.blit(ov, (0, 0))

        card_rect = self.rects["card"]
        cache_key = (self.engine.state, self.engine.score, self.engine.high_score, s["food_type"], s["snake_color"], s["theme"])
        if self._menu_card_cache is None or self._menu_card_key != cache_key:
            self._menu_card_cache = self._build_main_menu_card_2x(theme, s)
            self._menu_card_key = cache_key
        screen.blit(self._menu_card_cache, card_rect.topleft)

        btn_play = self.rects["btn_play"]
        btn_gear = self.rects["btn_side"]
        p_col = C.UI_BTN_BLUE_HOVER if btn_play.collidepoint(mouse_pos) else C.UI_BTN_BLUE
        g_col = C.UI_BTN_BLUE_HOVER if btn_gear.collidepoint(mouse_pos) else C.UI_BTN_BLUE
        I.draw_rounded_rect_aa(screen, p_col, btn_play, 8)
        I.draw_rounded_rect_aa(screen, g_col, btn_gear, 8)

        label = "Play Again" if self.engine.state == "WON" else "Play Snaky"
        p_txt = self.font_btn.render(label, True, C.UI_WHITE)
        total_w = 28 + p_txt.get_width()
        start_x = btn_play.centerx - total_w // 2
        I.draw_play_triangle(screen, start_x + 8, btn_play.centery, size=9)
        screen.blit(p_txt, p_txt.get_rect(midleft=(start_x + 28, btn_play.centery)))

        I.draw_gear_icon(screen, btn_gear.centerx, btn_gear.centery, radius=12, hole_color=g_col, outline_only=True)

    def _draw_carousel_icon(self, surf: pygame.Surface, row_idx: int, item_id: str, is_selected: bool) -> None:
        cx, cy = surf.get_width() // 2, surf.get_height() // 2
        if row_idx == 0:
            I.draw_fruit(surf, item_id, cx, cy + 1, 30, 0.92, (100, 140, 40), False, 255, False, 0.0, False)
        elif row_idx == 1:
            I.draw_mode_icon(surf, item_id, cx, cy, size=26)
        elif row_idx == 2:
            I.draw_count_icon(surf, item_id, cx, cy, is_selected)
        elif row_idx == 3:
            I.draw_speed_icon(surf, item_id, cx, cy)
        elif row_idx == 4:
            I.draw_board_size_icon(surf, item_id, cx, cy)
        elif row_idx == 5:
            I.draw_snake_ring_icon(surf, C.SNAKE_COLORS[item_id], cx, cy)
        elif row_idx == 6:
            I.draw_theme_icon(surf, item_id, cx, cy)
        elif row_idx == 7:
            I.draw_graphics_style_icon(surf, item_id, cx, cy)

    def _draw_settings_modal(self, screen: pygame.Surface, mouse_pos: Tuple[int, int], dt_sec: float) -> None:
        win_w, win_h = screen.get_size()
        s = self.settings_manager.get()
        rows_spec = self._get_rows_spec(s)

        ov = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 178))
        screen.blit(ov, (0, 0))

        card_rect = self.rects["card"]
        cw, ch = card_rect.width, card_rect.height
        card = pygame.Surface((cw, ch), pygame.SRCALPHA)
        card.fill(C.UI_CARD_SKY)

        # Exact 38px #3A91BB Header with white Back Arrow
        pygame.draw.rect(card, C.UI_SETTINGS_HEADER, (0, 0, cw, self.SETTINGS_HDR_H))
        back_local = pygame.Rect(6, 2, 34, 34)
        if self.rects["settings_back"].collidepoint(mouse_pos):
            I.draw_rounded_rect_aa(card, (255, 255, 255, 45), back_local, 17)
        I.draw_back_arrow(card, back_local.centerx, back_local.centery)

        self.carousel_item_rects = []
        self.carousel_row_rects = []
        self.hover_label = ""

        # 8 Exact 41px Carousel Rows with 3x SSAA Icons
        for row_idx, (cur_val, items, _) in enumerate(rows_spec):
            ry = self.SETTINGS_HDR_H + row_idx * self.ROW_H
            row_screen_rect = pygame.Rect(card_rect.left, card_rect.top + ry, cw, self.ROW_H)
            self.carousel_row_rects.append((row_screen_rect, row_idx))

            ids = [it[0] for it in items]
            active_idx = ids.index(cur_val) if cur_val in ids else 0
            target_off = (cw / 2.0) - (active_idx * self.SLOT_W + self.SLOT_W / 2.0)
            if not self._offsets_initialized:
                self.row_offsets[row_idx] = target_off
            else:
                self.row_offsets[row_idx] += (target_off - self.row_offsets[row_idx]) * min(1.0, dt_sec * 16.0)
            off_x = self.row_offsets[row_idx]

            for idx, (item_id, item_label) in enumerate(items):
                ix = int(round(off_x + idx * self.SLOT_W))
                if ix + self.SLOT_W < 0 or ix > cw:
                    continue
                item_screen_rect = pygame.Rect(card_rect.left + ix, card_rect.top + ry, self.SLOT_W, self.ROW_H - 1)
                self.carousel_item_rects.append((item_screen_rect, row_idx, item_id, item_label))

                is_sel = (item_id == cur_val)
                is_hov = item_screen_rect.collidepoint(mouse_pos)
                if is_hov:
                    self.hover_label = item_label

                icon_surf = pygame.Surface((self.SLOT_W, self.ROW_H - 1), pygame.SRCALPHA)
                self._draw_carousel_icon(icon_surf, row_idx, item_id, is_sel)
                if not is_sel:
                    icon_surf.set_alpha(200 if is_hov else 108)
                card.blit(icon_surf, (ix, ry))

            if row_idx < 7:
                pygame.draw.line(card, C.UI_SETTINGS_DIVIDER, (0, ry + self.ROW_H - 1), (cw, ry + self.ROW_H - 1), 1)

        self._offsets_initialized = True

        if self.hover_label:
            hl_txt = self.font_small.render(self.hover_label, True, (240, 250, 255))
            card.blit(hl_txt, hl_txt.get_rect(midright=(cw - 12, self.SETTINGS_HDR_H // 2)))

        # Blender Mix Popover
        self.blender_tile_rects = []
        if self.blender_open and s["mode"] == "blender":
            b_screen = self.rects["blender_box"]
            bx = b_screen.left - card_rect.left
            by = b_screen.top - card_rect.top
            bw, bh = b_screen.width, b_screen.height
            I.draw_rounded_rect_aa(card, (44, 119, 156), pygame.Rect(bx, by, bw, bh), 8, border_width=2, border_color=C.UI_SETTINGS_DIVIDER)

            bt = self.font_small.render(f"Blender Mix ({len(s['blender_modes'])} active)", True, C.UI_WHITE)
            card.blit(bt, (bx + 8, by + 6))

            cx_r = self.rects["blender_close"]
            cl_x, cl_y = cx_r.left - card_rect.left, cx_r.top - card_rect.top
            I.draw_rounded_rect_aa(card, (70, 145, 182), pygame.Rect(cl_x + 1, cl_y + 1, 20, 20), 10)
            x_txt = self.font_small.render("x", True, C.UI_WHITE)
            card.blit(x_txt, x_txt.get_rect(center=(cl_x + 11, cl_y + 10)))

            cell_w = (bw - 16) // 8
            cell_h = 28
            for idx, m in enumerate(C.BLENDABLE_MODES):
                col_i = idx % 8
                row_i = idx // 8
                tx = bx + 8 + col_i * cell_w
                ty = by + 26 + row_i * (cell_h + 3)
                t_rect_local = pygame.Rect(tx, ty, cell_w - 3, cell_h)
                t_rect_screen = pygame.Rect(card_rect.left + tx, card_rect.top + ty, cell_w - 3, cell_h)
                self.blender_tile_rects.append((t_rect_screen, m["id"]))

                on = m["id"] in s["blender_modes"]
                bg = C.UI_BTN_BLUE if on else (65, 138, 176)
                I.draw_rounded_rect_aa(card, bg, t_rect_local, 5, border_width=1 if on else 0, border_color=C.UI_WHITE if on else None)
                msurf = pygame.Surface((t_rect_local.width, t_rect_local.height), pygame.SRCALPHA)
                I.draw_mode_icon(msurf, m["id"], msurf.get_width() // 2, msurf.get_height() // 2, size=18)
                if not on:
                    msurf.set_alpha(120)
                card.blit(msurf, t_rect_local.topleft)

        # Clip Settings Card with color-matched white alpha mask (ZERO dark corner halo!)
        mask_2x = pygame.Surface((cw * 2, ch * 2), pygame.SRCALPHA)
        mask_2x.fill((255, 255, 255, 0))
        pygame.draw.rect(mask_2x, (255, 255, 255, 255), (0, 0, cw * 2, ch * 2), border_radius=16)
        mask = pygame.transform.smoothscale(mask_2x, (cw, ch))
        card.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(card, card_rect.topleft)

        # Bottom Action Row: 224x64 Play Snaky + 64x64 Dice Randomizer
        btn_play = self.rects["btn_play"]
        btn_dice = self.rects["btn_side"]
        p_col = C.UI_BTN_BLUE_HOVER if btn_play.collidepoint(mouse_pos) else C.UI_BTN_BLUE
        d_col = C.UI_BTN_BLUE_HOVER if btn_dice.collidepoint(mouse_pos) else C.UI_BTN_BLUE
        I.draw_rounded_rect_aa(screen, p_col, btn_play, 8)
        I.draw_rounded_rect_aa(screen, d_col, btn_dice, 8)

        p_txt = self.font_btn.render("Play Snaky", True, C.UI_WHITE)
        total_w = 28 + p_txt.get_width()
        start_x = btn_play.centerx - total_w // 2
        I.draw_play_triangle(screen, start_x + 8, btn_play.centery, size=9)
        screen.blit(p_txt, p_txt.get_rect(midleft=(start_x + 28, btn_play.centery)))

        I.draw_dice_icon(screen, btn_dice.centerx, btn_dice.centery, size=28.0, bg=C.UI_WHITE, dot=d_col, five=False)

    def render(self, screen: pygame.Surface, board_surface: pygame.Surface, mouse_pos: Tuple[int, int], dt_sec: float) -> None:
        theme = C.THEMES.get(self.settings_manager.get()["theme"], C.THEMES["classic"])

        screen.fill(theme["border"])
        screen.blit(board_surface, self.board_origin)

        self._draw_top_bar(screen, theme, mouse_pos)

        if self.is_settings_open:
            self._draw_settings_modal(screen, mouse_pos, dt_sec)
        elif self.engine.state == "PAUSED":
            self._draw_pause_ui(screen, theme, mouse_pos)
        elif self.engine.state in ("MENU", "GAMEOVER", "WON"):
            self._draw_main_menu_modal(screen, theme, mouse_pos)
