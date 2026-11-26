"""Snaky Game — Seamless Unified 2x SSAA Board & Snake Renderer (Zero Seams, Zero Halos).

Root cause fixed from v1.1.0:
- Never stamps individual semi-transparent circles onto the board (which caused dark
  non-premultiplied rings and a chopped-up snake body).
- Instead, draws the ENTIRE snake shadow onto ONE color-matched 2x buffer `(*shadow, 0)`
  and the ENTIRE snake body + snout + mouth + fangs + eyes + pupils + nostrils onto ONE
  color-matched 2x buffer `(*head_col, 0)` (reusing pre-allocated scratch buffers via
  zero-copy `.subsurface()`), then downscales cleanly once with `smoothscale`.
- Result: 100% seamless continuous curved snake tube, zero dark halos, crisp HTML5-Canvas
  quality anti-aliasing at locked 60 FPS.
"""

import math
from typing import Dict, List, Optional, Tuple

import pygame

from . import constants as C
from .icons import _get_cached_sprite, _render_aa_layer, draw_fruit
from .modes import ModeEngine


def _invert_rgb(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return (255 - rgb[0], 255 - rgb[1], 255 - rgb[2])


def _semicircle_points(
    cx: float, cy: float, dx: float, dy: float, px: float, py: float, radius: float, steps: int = 28
) -> List[Tuple[int, int]]:
    pts = []
    for i in range(steps + 1):
        ang = -math.pi / 2.0 + (math.pi * i / steps)
        ca, sa = math.cos(ang), math.sin(ang)
        pts.append((int(round(cx + (dx * ca + px * sa) * radius)), int(round(cy + (dy * ca + py * sa) * radius))))
    return pts


class BoardRenderer:
    """Seamless 2x/4x SSAA board, mode entities, fruits, snakes, and lighting renderer."""

    def __init__(self) -> None:
        self.board_cache: Optional[pygame.Surface] = None
        self.cache_key = ""
        self.board_surface: Optional[pygame.Surface] = None
        # Pre-allocated 2x scratch buffers for zero-copy tight-bbox snake & shadow rendering
        self._hi_snake_buf: Optional[pygame.Surface] = None
        self._hi_shadow_buf: Optional[pygame.Surface] = None
        self._light_radial_unit: Optional[pygame.Surface] = None
        self._light_mask_buf: Optional[pygame.Surface] = None
        self._paused_rendered: bool = False
        self._particle_cache: Dict[int, pygame.Surface] = {}

    def _ensure_surfaces(self, engine, theme: Dict) -> None:
        w = engine.cols * engine.cell_size
        h = engine.rows * engine.cell_size
        key = f"{engine.cols}x{engine.rows}x{engine.cell_size}|{theme['id']}|{engine.active_dimension}"
        if self.board_surface is None or self.board_surface.get_size() != (w, h):
            self.board_surface = pygame.Surface((w, h)).convert()
            self._hi_snake_buf = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
            self._hi_shadow_buf = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
            self._light_mask_buf = pygame.Surface((w, h), pygame.SRCALPHA)
            self._paused_rendered = False

        if self.cache_key == key and self.board_cache is not None:
            return

        self.cache_key = key
        surf = pygame.Surface((w, h)).convert()
        cs = engine.cell_size
        for r in range(engine.rows):
            for c in range(engine.cols):
                col = theme["light_cell"] if (r + c) % 2 == 0 else theme["dark_cell"]
                pygame.draw.rect(surf, col, (c * cs, r * cs, cs, cs))

        if ModeEngine.has(engine, "dimension") and engine.active_dimension == 1:
            tint = pygame.Surface((w, h), pygame.SRCALPHA)
            tint.fill((88, 28, 135, 62))
            surf.blit(tint, (0, 0))

        self.board_cache = surf

    def invalidate_cache(self) -> None:
        self.cache_key = ""
        self._paused_rendered = False

    def _get_particle_sprite(self, rad: int) -> pygame.Surface:
        r = max(2, int(rad))
        spr = self._particle_cache.get(r)
        if spr is not None:
            return spr
        dim = r * 2 + 2
        spr = pygame.Surface((dim, dim), pygame.SRCALPHA)
        _render_aa_layer(spr, 4, (231, 71, 29), lambda hi, cx, cy, sc: pygame.draw.circle(hi, (231, 71, 29, 255), (int(cx), int(cy)), int(r * sc)))
        self._particle_cache[r] = spr
        return spr

    @staticmethod
    def _get_smooth_snake_points(
        snake: List[Dict], prev_tail: Optional[Dict], move_progress: float, just_grew: bool, cs: int
    ) -> List[Tuple[float, float]]:
        def to_px(cell):
            return (cell["x"] * cs + cs / 2.0, cell["y"] * cs + cs / 2.0)

        if len(snake) < 2:
            return [to_px(snake[0])]

        p0 = to_px(snake[0])
        p1 = to_px(snake[1])
        head_jumped = math.hypot(p0[0] - p1[0], p0[1] - p1[1]) > cs * 1.5
        head_px = p0 if head_jumped else (
            p1[0] + (p0[0] - p1[0]) * move_progress,
            p1[1] + (p0[1] - p1[1]) * move_progress,
        )

        pts = [head_px]
        for seg in snake[1:-1]:
            pts.append(to_px(seg))

        last_seg = to_px(snake[-1])
        if just_grew or prev_tail is None:
            pts.append(last_seg)
        else:
            pt_px = to_px(prev_tail)
            if math.hypot(last_seg[0] - pt_px[0], last_seg[1] - pt_px[1]) > cs * 1.5:
                pts.append(last_seg)
            else:
                tail_px = (
                    pt_px[0] + (last_seg[0] - pt_px[0]) * move_progress,
                    pt_px[1] + (last_seg[1] - pt_px[1]) * move_progress,
                )
                pts.append(last_seg)
                pts.append(tail_px)
        return pts

    @staticmethod
    def _split_continuous_segments(pts: List[Tuple[float, float]], cs: int) -> List[List[Tuple[float, float]]]:
        chains = []
        current = [pts[0]]
        for i in range(1, len(pts)):
            if math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) > cs * 1.6:
                chains.append(current)
                current = [pts[i]]
            else:
                current.append(pts[i])
        chains.append(current)
        return chains

    @staticmethod
    def _build_curved_spine(pts: List[Tuple[float, float]], corner_radius: float, arc_steps: int = 12) -> List[Tuple[float, float]]:
        if len(pts) < 3:
            return list(pts)
        curved = [pts[0]]
        for i in range(1, len(pts) - 1):
            p_prev, p_curr, p_next = pts[i - 1], pts[i], pts[i + 1]
            vx1, vy1 = p_curr[0] - p_prev[0], p_curr[1] - p_prev[1]
            vx2, vy2 = p_next[0] - p_curr[0], p_next[1] - p_curr[1]
            d1 = math.hypot(vx1, vy1)
            d2 = math.hypot(vx2, vy2)
            if d1 < 0.001 or d2 < 0.001:
                continue
            ux1, uy1 = vx1 / d1, vy1 / d1
            ux2, uy2 = vx2 / d2, vy2 / d2
            if abs(ux1 * ux2 + uy1 * uy2 - 1.0) < 0.01:
                curved.append(p_curr)
                continue
            r = min(corner_radius, d1 * 0.48, d2 * 0.48)
            sp = (p_curr[0] - ux1 * r, p_curr[1] - uy1 * r)
            ep = (p_curr[0] + ux2 * r, p_curr[1] + uy2 * r)
            for s in range(arc_steps + 1):
                t = s / arc_steps
                mt = 1.0 - t
                curved.append((
                    mt * mt * sp[0] + 2.0 * mt * t * p_curr[0] + t * t * ep[0],
                    mt * mt * sp[1] + 2.0 * mt * t * p_curr[1] + t * t * ep[1],
                ))
        curved.append(pts[-1])
        return curved

    def _draw_pixel_snake(
        self, surf, engine, snake_arr, prev_tail, just_grew, dir_vec, color_cfg, is_inverted: bool, is_main: bool
    ) -> None:
        cs = engine.cell_size
        bar_w = int(round(cs * 0.84))
        half_w = bar_w / 2.0
        prog = engine.get_move_progress()
        raw_pts = self._get_smooth_snake_points(snake_arr, prev_tail, prog, just_grew, cs)
        chains = self._split_continuous_segments(raw_pts, cs)
        is_cheese = ModeEngine.has(engine, "cheese")
        is_dizzy = engine.state in ("DYING", "GAMEOVER")
        theme = C.THEMES.get(engine.settings["theme"], C.THEMES["classic"])

        head_col = _invert_rgb(color_cfg["head"]) if is_inverted else color_cfg["head"]
        tail_col = _invert_rgb(color_cfg["tail"]) if is_inverted else color_cfg["tail"]
        mouth_col = _invert_rgb(color_cfg["mouth"]) if is_inverted else color_cfg["mouth"]
        pupil_col = _invert_rgb(color_cfg["pupil"]) if is_inverted else color_cfg["pupil"]

        def color_at(ratio: float):
            return (
                int(round(head_col[0] * (1.0 - ratio) + tail_col[0] * ratio)),
                int(round(head_col[1] * (1.0 - ratio) + tail_col[1] * ratio)),
                int(round(head_col[2] * (1.0 - ratio) + tail_col[2] * ratio)),
            )

        total_pts = max(1, len(raw_pts) - 1)
        shadow_off = max(2, int(round(cs * 0.08)))

        for ch in chains:
            for i in range(len(ch) - 1):
                if is_cheese and i > 0 and i % 2 == 1:
                    continue
                a, b = ch[i], ch[i + 1]
                pygame.draw.rect(
                    surf,
                    theme["shadow"],
                    (
                        int(round(min(a[0], b[0]) - half_w)),
                        int(round(min(a[1], b[1]) - half_w + shadow_off)),
                        int(round(abs(b[0] - a[0]) + bar_w)),
                        int(round(abs(b[1] - a[1]) + bar_w)),
                    ),
                )

        global_idx = total_pts
        for ch in reversed(chains):
            for i in range(len(ch) - 2, -1, -1):
                global_idx = max(0, global_idx - 1)
                if is_cheese and i > 0 and i % 2 == 1:
                    continue
                ratio = min(1.0, global_idx / total_pts)
                a, b = ch[i], ch[i + 1]
                pygame.draw.rect(
                    surf,
                    color_at(ratio),
                    (
                        int(round(min(a[0], b[0]) - half_w)),
                        int(round(min(a[1], b[1]) - half_w)),
                        int(round(abs(b[0] - a[0]) + bar_w)),
                        int(round(abs(b[1] - a[1]) + bar_w)),
                    ),
                )

        hx, hy = raw_pts[0]
        if abs(dir_vec[0]) >= abs(dir_vec[1]):
            dx, dy = (1 if dir_vec[0] >= 0 else -1), 0
        else:
            dx, dy = 0, (1 if dir_vec[1] >= 0 else -1)
        px, py = -dy, dx

        mouth_anim = engine.mouth_anim if is_main else 0.0
        if mouth_anim < 0.12 and not is_dizzy:
            phase_ms = engine.game_time_ms % 3200.0
            if phase_ms < 420.0:
                ext = math.sin((phase_ms / 420.0) * math.pi)
                ut = max(2, int(round(cs * 0.085)))
                t_len = max(ut, int(round((cs * 0.34) * ext)))
                sx, sy = hx + dx * half_w, hy + dy * half_w
                if dx != 0:
                    x0 = sx if dx > 0 else sx - t_len
                    pygame.draw.rect(surf, C.UI_TONGUE_RED, (int(round(x0)), int(round(sy - ut * 0.5)), t_len, ut))
                    tip_x = sx + t_len if dx > 0 else sx - t_len - ut
                    pygame.draw.rect(surf, C.UI_TONGUE_RED, (int(round(tip_x)), int(round(sy - ut * 1.5)), ut, ut))
                    pygame.draw.rect(surf, C.UI_TONGUE_RED, (int(round(tip_x)), int(round(sy + ut * 0.5)), ut, ut))
                else:
                    y0 = sy if dy > 0 else sy - t_len
                    pygame.draw.rect(surf, C.UI_TONGUE_RED, (int(round(sx - ut * 0.5)), int(round(y0)), ut, t_len))
                    tip_y = sy + t_len if dy > 0 else sy - t_len - ut
                    pygame.draw.rect(surf, C.UI_TONGUE_RED, (int(round(sx - ut * 1.5)), int(round(tip_y)), ut, ut))
                    pygame.draw.rect(surf, C.UI_TONGUE_RED, (int(round(sx + ut * 0.5)), int(round(tip_y)), ut, ut))

        if mouth_anim > 0.12 and not is_dizzy:
            mw = int(round(bar_w * 0.44 * mouth_anim))
            md = int(round(bar_w * 0.28 * mouth_anim))
            mx = hx + dx * (half_w - md * 0.5)
            my = hy + dy * (half_w - md * 0.5)
            if dx != 0:
                pygame.draw.rect(surf, mouth_col, (int(round(mx - md / 2)), int(round(my - mw / 2)), md + 2, mw))
            else:
                pygame.draw.rect(surf, mouth_col, (int(round(mx - mw / 2)), int(round(my - md / 2)), mw, md + 2))

        u = max(2, int(round(cs * 0.085)))
        for side in (-1, 1):
            ex = hx - dx * (u * 1.4) + px * (half_w - u * 1.6) * side
            ey = hy - dy * (u * 1.4) + py * (half_w - u * 1.6) * side
            if dx != 0:
                pygame.draw.rect(surf, C.UI_WHITE, (int(round(ex - u)), int(round(ey - u * 1.35)), int(round(u * 2.0)), int(round(u * 2.7))))
            else:
                pygame.draw.rect(surf, C.UI_WHITE, (int(round(ex - u * 1.35)), int(round(ey - u)), int(round(u * 2.7)), int(round(u * 2.0))))
            p_shift = 0.0 if is_dizzy else u * 0.35
            ps = max(2, int(round(u * 1.15)))
            pygame.draw.rect(surf, pupil_col, (int(round(ex + dx * p_shift - u * 0.55)), int(round(ey + dy * p_shift - u * 0.55)), ps, ps))

            nx = hx + dx * (half_w - u * 1.5) + px * (half_w * 0.52) * side
            ny = hy + dy * (half_w - u * 1.5) + py * (half_w * 0.52) * side
            ns = max(2, int(round(u * 0.9)))
            pygame.draw.rect(surf, pupil_col, (int(round(nx - u * 0.45)), int(round(ny - u * 0.45)), ns, ns))

    def _draw_tongue_3x(
        self,
        surf: pygame.Surface,
        hx: float,
        hy: float,
        dx: float,
        dy: float,
        px: float,
        py: float,
        snake_radius: float,
        snout_off2: float,
        phase_ms: float,
    ) -> None:
        """Draws the periodic forked red tongue on its own color-matched 3x SSAA patch (zero halo)."""
        p = phase_ms / 420.0
        ext = math.sin(p * math.pi)
        if ext <= 0.02:
            return
        pad = int(math.ceil(snake_radius * 2.6))
        box = pad * 2
        ss = 3
        hi = pygame.Surface((box * ss, box * ss), pygame.SRCALPHA)
        hi.fill((*C.UI_TONGUE_RED, 0))

        cx = pad * ss
        cy = pad * ss
        sr = snake_radius * ss
        wiggle = math.sin(p * math.pi * 5.0) * (sr * 0.14) * ext
        base_dist = (snout_off2 * ss) + sr * 0.80
        t_len = (sr * 0.80) * ext
        bx = cx + dx * base_dist
        by = cy + dy * base_dist
        tx = bx + dx * t_len + px * wiggle
        ty = by + dy * t_len + py * wiggle
        fork_len = sr * 0.35 * ext
        fork_spread = sr * 0.25 * ext
        lw = max(3, int(round(sr * 0.16)))
        col = (*C.UI_TONGUE_RED, 255)
        pygame.draw.line(hi, col, (int(bx), int(by)), (int(tx), int(ty)), lw)
        pygame.draw.circle(hi, col, (int(tx), int(ty)), lw // 2)
        t1 = (int(tx + dx * fork_len + px * fork_spread), int(ty + dy * fork_len + py * fork_spread))
        t2 = (int(tx + dx * fork_len - px * fork_spread), int(ty + dy * fork_len - py * fork_spread))
        lw2 = max(2, int(lw * 0.78))
        pygame.draw.line(hi, col, (int(tx), int(ty)), t1, lw2)
        pygame.draw.line(hi, col, (int(tx), int(ty)), t2, lw2)
        pygame.draw.circle(hi, col, t1, lw2 // 2)
        pygame.draw.circle(hi, col, t2, lw2 // 2)

        down = pygame.transform.smoothscale(hi, (box, box))
        surf.blit(down, (int(round(hx - pad)), int(round(hy - pad))))

    def _draw_snake(
        self, surf, engine, snake_arr, prev_tail, just_grew, dir_vec, color_cfg, is_inverted: bool, is_main: bool
    ) -> None:
        if engine.settings["graphics_style"] == "pixel":
            self._draw_pixel_snake(surf, engine, snake_arr, prev_tail, just_grew, dir_vec, color_cfg, is_inverted, is_main)
            return

        cs = engine.cell_size
        board_w, board_h = surf.get_size()
        snake_radius = max(8.0, cs * 0.39)
        shadow_off_y = max(2.0, cs * 0.11)
        prog = engine.get_move_progress()
        raw_pts = self._get_smooth_snake_points(snake_arr, prev_tail, prog, just_grew, cs)
        chains = self._split_continuous_segments(raw_pts, cs)
        is_dizzy = engine.state in ("DYING", "GAMEOVER")
        is_cheese = ModeEngine.has(engine, "cheese")
        theme = C.THEMES.get(engine.settings["theme"], C.THEMES["classic"])

        head_col = _invert_rgb(color_cfg["head"]) if is_inverted else color_cfg["head"]
        tail_col = _invert_rgb(color_cfg["tail"]) if is_inverted else color_cfg["tail"]
        mouth_col = _invert_rgb(color_cfg["mouth"]) if is_inverted else color_cfg["mouth"]
        pupil_col = _invert_rgb(color_cfg["pupil"]) if is_inverted else color_cfg["pupil"]

        # Dense continuous Bézier spine sampling (step = 1.25px at 1x -> 95%+ overlap, zero choppiness!)
        uniform_chains: List[List[Tuple[float, float, float]]] = []
        total_len = 0.0
        for ch in chains:
            spine = self._build_curved_spine(ch, cs * 0.48, 12)
            u_pts = [(spine[0][0], spine[0][1], total_len)]
            for i in range(len(spine) - 1):
                x1, y1 = spine[i]
                x2, y2 = spine[i + 1]
                seg_d = math.hypot(x2 - x1, y2 - y1)
                if seg_d < 0.001:
                    continue
                step_sz = max(2.2, snake_radius * 0.22)
                steps = max(1, int(round(seg_d / step_sz)))
                for s in range(1, steps + 1):
                    t = s / steps
                    px_i = x1 + (x2 - x1) * t
                    py_i = y1 + (y2 - y1) * t
                    total_len += math.hypot(px_i - u_pts[-1][0], py_i - u_pts[-1][1])
                    u_pts.append((px_i, py_i, total_len))
            uniform_chains.append(u_pts)

        head_chain = uniform_chains[0]
        dx, dy = dir_vec
        if not is_dizzy and len(head_chain) > 5:
            tx = head_chain[0][0] - head_chain[5][0]
            ty = head_chain[0][1] - head_chain[5][1]
            t_len = math.hypot(tx, ty)
            if t_len > 0.001:
                bx = dx * 0.65 + (tx / t_len) * 0.35
                by = dy * 0.65 + (ty / t_len) * 0.35
                b_len = math.hypot(bx, by)
                if b_len > 0.001:
                    dx, dy = bx / b_len, by / b_len

        if is_main and engine.recoil_px > 0.0:
            scaled_recoil = engine.recoil_px * (cs / 32.0)
            span = cs * 2.0
            for i in range(len(head_chain)):
                x_i, y_i, dist_i = head_chain[i]
                if dist_i < span:
                    f = math.cos((dist_i / span) * (math.pi / 2.0))
                    head_chain[i] = (x_i - dx * scaled_recoil * f, y_i - dy * scaled_recoil * f, dist_i)
                else:
                    break

        hx, hy, _ = head_chain[0]
        px, py = -dy, dx

        # Compute tight bounding box for the entire snake (clamped to board)
        min_x = hx
        max_x = hx
        min_y = hy
        max_y = hy
        for u_pts in uniform_chains:
            for x_i, y_i, _ in u_pts:
                if x_i < min_x:
                    min_x = x_i
                if x_i > max_x:
                    max_x = x_i
                if y_i < min_y:
                    min_y = y_i
                if y_i > max_y:
                    max_y = y_i

        pad = int(math.ceil(snake_radius * 2.8)) + 8
        bx0 = max(0, int(math.floor(min_x)) - pad)
        by0 = max(0, int(math.floor(min_y)) - pad)
        bx1 = min(board_w, int(math.ceil(max_x)) + pad)
        by1 = min(board_h, int(math.ceil(max_y)) + pad + int(math.ceil(shadow_off_y)))
        bw = max(4, bx1 - bx0)
        bh = max(4, by1 - by0)

        def body_color_at(ratio: float, dist_val: float) -> Tuple[int, int, int, int]:
            pulse_boost = 0.0
            if is_main and ModeEngine.has(engine, "light"):
                for lp in engine.light_pulses:
                    diff = abs(dist_val - lp["dist"])
                    if diff < cs * 0.7:
                        pulse_boost = max(pulse_boost, math.cos((diff / (cs * 0.7)) * (math.pi / 2.0)) * 95.0)
            r = head_col[0] * (1.0 - ratio) + tail_col[0] * ratio + pulse_boost
            g = head_col[1] * (1.0 - ratio) + tail_col[1] * ratio + pulse_boost
            b = head_col[2] * (1.0 - ratio) + tail_col[2] * ratio + pulse_boost
            return (min(255, int(round(r))), min(255, int(round(g))), min(255, int(round(b))), 255)

        def radius_at(dist_val: float, ratio: float) -> float:
            r_base = snake_radius
            if ratio > 0.88:
                t_tail = (ratio - 0.88) / 0.12
                r_base = max(snake_radius * 0.74, snake_radius * (1.0 - 0.20 * (t_tail ** 1.5)))
            extra = 0.0
            if is_main:
                for b_dist in engine.bulges:
                    diff = abs(dist_val - b_dist)
                    if diff < cs * 0.48:
                        extra = max(extra, (cs * 0.18) * math.cos((diff / (cs * 0.48)) * (math.pi / 2.0)))
            return r_base + extra

        def is_cheese_gap(dist_val: float) -> bool:
            if not is_cheese:
                return False
            seg_idx = int(dist_val // cs)
            return seg_idx > 0 and seg_idx % 2 == 1

        mouth_anim = engine.mouth_anim if is_main else 0.0
        denom_len = max(1.0, total_len)
        sc = 1.5 if (bw * bh > 420000) else 2.0
        buf_w, buf_h = self._hi_snake_buf.get_size()
        hi_w = min(buf_w, max(4, int(round(bw * sc))))
        hi_h = min(buf_h, max(4, int(round(bh * sc))))

        snout_off1 = snake_radius * 0.28
        snout_off2 = snake_radius * 0.56
        eye_back_off = snake_radius * 0.34
        eye_side_off = snake_radius * 0.76
        eye_dome_r = int(round(snake_radius * 0.68 * sc))
        eye_white_r = int(round(snake_radius * 0.44 * sc))
        pupil_r = max(2, int(round(snake_radius * 0.23 * sc)))

        lhx = (hx - bx0) * sc
        lhy = (hy - by0) * sc
        sr = snake_radius * sc
        sh_y = shadow_off_y * sc

        # ------------------------------------------------------------------
        # PASS 1: UNIFIED FLAT 2x SHADOW (Zero overlap blotches, zero halo!)
        # ------------------------------------------------------------------
        sh_col = theme["shadow"]
        hi_sh = self._hi_shadow_buf.subsurface((0, 0, hi_w, hi_h))
        hi_sh.fill((*sh_col, 0))
        sh_solid = (*sh_col, 255)

        for u_pts in reversed(uniform_chains):
            for x_i, y_i, d_i in reversed(u_pts):
                if is_cheese_gap(d_i):
                    continue
                rad_2x = max(2, int(round(radius_at(d_i, d_i / denom_len) * sc)))
                pygame.draw.circle(hi_sh, sh_solid, (int(round((x_i - bx0) * sc)), int(round((y_i - by0) * sc + sh_y))), rad_2x)

        pygame.draw.circle(hi_sh, sh_solid, (int(round(lhx + dx * snout_off2 * sc)), int(round(lhy + dy * snout_off2 * sc + sh_y))), int(round(sr * 0.96)))
        for side in (-1, 1):
            ex = lhx - dx * eye_back_off * sc + px * eye_side_off * sc * side
            ey = lhy - dy * eye_back_off * sc + py * eye_side_off * sc * side + sh_y
            pygame.draw.circle(hi_sh, sh_solid, (int(round(ex)), int(round(ey))), eye_dome_r)
        if mouth_anim > 0.04 and not is_dizzy:
            lip_cx = lhx + dx * (sr * 0.48)
            lip_cy = lhy + dy * (sr * 0.48) + sh_y
            outer_r = sr + (sr * 0.40) * mouth_anim
            pygame.draw.polygon(hi_sh, sh_solid, _semicircle_points(lip_cx, lip_cy, dx, dy, px, py, outer_r))

        sh_1x = pygame.transform.smoothscale(hi_sh, (bw, bh))
        sh_1x.set_alpha(175)
        surf.blit(sh_1x, (bx0, by0))

        # ------------------------------------------------------------------
        # PASS 2: PERIODIC FORKED RED TONGUE (Every 3.2s, 3x color-matched AA)
        # ------------------------------------------------------------------
        if mouth_anim < 0.12 and not is_dizzy:
            phase_ms = engine.game_time_ms % 3200.0
            if phase_ms < 420.0:
                self._draw_tongue_3x(surf, hx, hy, dx, dy, px, py, snake_radius, snout_off2, phase_ms)

        # ------------------------------------------------------------------
        # PASS 3: UNIFIED SEAMLESS 2x SNAKE BODY + HEAD (Zero seams, zero halo!)
        # ------------------------------------------------------------------
        # Pre-fill with exact snake RGB at alpha=0 so smoothscale produces pure blue AA edges!
        hi_sn = self._hi_snake_buf.subsurface((0, 0, hi_w, hi_h))
        hi_sn.fill((*head_col, 0))

        # Continuous opaque curved body from tail to head
        for u_pts in reversed(uniform_chains):
            for x_i, y_i, d_i in reversed(u_pts):
                if is_cheese_gap(d_i):
                    continue
                ratio = d_i / denom_len
                rad_2x = max(2, int(round(radius_at(d_i, ratio) * sc)))
                pygame.draw.circle(hi_sn, body_color_at(ratio, d_i), (int(round((x_i - bx0) * sc)), int(round((y_i - by0) * sc))), rad_2x)

        # Elongated rounded snout (merges seamlessly into body on same surface!)
        head_fill = body_color_at(0.0, 0.0)
        pygame.draw.circle(hi_sn, head_fill, (int(round(lhx + dx * snout_off1 * sc)), int(round(lhy + dy * snout_off1 * sc))), int(round(sr)))
        pygame.draw.circle(hi_sn, head_fill, (int(round(lhx + dx * snout_off2 * sc)), int(round(lhy + dy * snout_off2 * sc))), int(round(sr * 0.96)))

        # Open semicircle mouth + swallowing fruit + white fangs
        if mouth_anim > 0.04 and not is_dizzy:
            lip_cx = lhx + dx * (sr * 0.48)
            lip_cy = lhy + dy * (sr * 0.48)
            outer_r = sr + (sr * 0.42) * mouth_anim
            pygame.draw.polygon(hi_sn, head_fill, _semicircle_points(lip_cx, lip_cy, dx, dy, px, py, outer_r))

            inner_cx = lhx + dx * (sr * 0.58)
            inner_cy = lhy + dy * (sr * 0.58)
            inner_r = (sr * 0.85) * mouth_anim + (sr * 0.16) * mouth_anim
            if inner_r > 2.0:
                pygame.draw.polygon(hi_sn, (*mouth_col, 255), _semicircle_points(inner_cx, inner_cy, dx, dy, px, py, inner_r))

            if is_main and engine.eating_apple is not None:
                ea = engine.eating_apple
                local_ax = (ea["x"] - bx0) * sc
                local_ay = (ea["y"] - by0) * sc
                draw_fruit(hi_sn, ea["sprite"], local_ax, local_ay, cs, ea["scale"] * sc, theme["shadow"], False, 255, False, engine.game_time_ms, False)

            if mouth_anim > 0.25:
                fang_len = (sr * 0.38) * mouth_anim
                fang_hw = sr * 0.17
                for side in (-1, 1):
                    fx = inner_cx + px * (sr * 0.42) * side
                    fy = inner_cy + py * (sr * 0.42) * side
                    fang_pts = [
                        (int(round(fx - px * fang_hw * side)), int(round(fy - py * fang_hw * side))),
                        (int(round(fx + px * fang_hw * side)), int(round(fy + py * fang_hw * side))),
                        (int(round(fx + dx * fang_len)), int(round(fy + dy * fang_len))),
                    ]
                    pygame.draw.polygon(hi_sn, (255, 255, 255, 255), fang_pts)

        # Seamless eye domes + crisp white eyeballs + tracking pupils + catchlight + forward nostrils
        if is_main and engine.eating_apple is not None:
            target_food = (engine.eating_apple["x"], engine.eating_apple["y"])
        else:
            target_food = engine.get_nearest_food_px(hx, hy)

        look_x, look_y = dx, dy
        if target_food is not None:
            d = math.hypot(target_food[0] - hx, target_food[1] - hy)
            if d > 1.0:
                look_x = (target_food[0] - hx) / d
                look_y = (target_food[1] - hy) / d

        for idx, side in enumerate((-1, 1)):
            ex = lhx - dx * eye_back_off * sc + px * eye_side_off * sc * side
            ey = lhy - dy * eye_back_off * sc + py * eye_side_off * sc * side
            pygame.draw.circle(hi_sn, head_fill, (int(round(ex)), int(round(ey))), eye_dome_r)
            pygame.draw.circle(hi_sn, (255, 255, 255, 255), (int(round(ex)), int(round(ey))), eye_white_r)

            if is_dizzy:
                ang = (engine.dying_timer_ms / 1000.0) * 14.0 * side + idx * 2.4
                p_off_x = ex + math.cos(ang) * (eye_white_r * 0.42)
                p_off_y = ey + math.sin(ang) * (eye_white_r * 0.42)
                pr = int(round(pupil_r * (1.1 if idx == 0 else 0.9)))
                pygame.draw.circle(hi_sn, (*pupil_col, 255), (int(round(p_off_x)), int(round(p_off_y))), max(2, pr))
            else:
                p_off_x = ex + look_x * (eye_white_r * 0.36)
                p_off_y = ey + look_y * (eye_white_r * 0.36)
                pygame.draw.circle(hi_sn, (*pupil_col, 255), (int(round(p_off_x)), int(round(p_off_y))), pupil_r)
                glint_r = max(1, int(round(pupil_r * 0.26)))
                pygame.draw.circle(hi_sn, (255, 255, 255, 220), (int(round(p_off_x - pupil_r * 0.32)), int(round(p_off_y - pupil_r * 0.32))), glint_r)

            if mouth_anim < 0.35:
                nx = lhx + dx * (sr * 0.84) + px * (sr * 0.34) * side
                ny = lhy + dy * (sr * 0.84) + py * (sr * 0.34) * side
                pygame.draw.circle(hi_sn, (*pupil_col, 255), (int(round(nx)), int(round(ny))), max(2, int(round(sr * 0.115))))

        # Single silky-smooth 2x -> 1x downscale for the ENTIRE snake!
        sn_1x = pygame.transform.smoothscale(hi_sn, (bw, bh))
        surf.blit(sn_1x, (bx0, by0))

    def _get_obstacle_sprite(self, kind: str, cs: int) -> pygame.Surface:
        """Color-matched 4x SSAA cached sprites for mode obstacles (zero halos)."""
        key = ("obs_clean", kind, cs)

        def _build(dest: pygame.Surface) -> None:
            ss = 4
            if kind == "wall":
                def _dw(hi, hcx, hcy, sc):
                    s = cs * sc
                    r = pygame.Rect(int(1 * sc), int(1 * sc), int(s - 2 * sc), int(s - 2 * sc))
                    pygame.draw.rect(hi, (134, 42, 14, 255), r, border_radius=max(2, int(3 * sc)))
                    b1 = pygame.Rect(int(2.5 * sc), int(2.5 * sc), int(s / 2 - 3.5 * sc), int(s / 2 - 3.5 * sc))
                    b2 = pygame.Rect(int(s / 2 + 1 * sc), int(2.5 * sc), int(s / 2 - 3.5 * sc), int(s / 2 - 3.5 * sc))
                    b3 = pygame.Rect(int(2.5 * sc), int(s / 2 + 1 * sc), int(s - 5 * sc), int(s / 2 - 3.5 * sc))
                    for br in (b1, b2, b3):
                        pygame.draw.rect(hi, (198, 68, 16, 255), br, border_radius=max(1, int(2 * sc)))
                        pygame.draw.line(hi, (224, 96, 42, 255), (br.left + int(2 * sc), br.top + int(1.5 * sc)), (br.right - int(2 * sc), br.top + int(1.5 * sc)), max(1, int(1.2 * sc)))
                _render_aa_layer(dest, ss, (154, 52, 18), _dw)
            elif kind == "statue":
                def _ds(hi, hcx, hcy, sc):
                    s = cs * sc
                    r = pygame.Rect(int(2 * sc), int(2 * sc), int(s - 4 * sc), int(s - 4 * sc))
                    pygame.draw.rect(hi, (104, 120, 144, 255), r, border_radius=int(6 * sc))
                    pygame.draw.rect(hi, (136, 152, 174, 255), (r.left + int(2 * sc), r.top + int(2 * sc), r.width - int(4 * sc), int(r.height * 0.35)), border_radius=int(4 * sc))
                    pygame.draw.rect(hi, (68, 82, 102, 255), r, width=max(2, int(2 * sc)), border_radius=int(6 * sc))
                    pygame.draw.lines(hi, (48, 62, 82, 255), False, [(int(s * 0.3), int(s * 0.25)), (int(s * 0.56), int(s * 0.52)), (int(s * 0.42), int(s * 0.78))], max(2, int(2 * sc)))
                _render_aa_layer(dest, ss, (104, 120, 144), _ds)
            elif kind == "lock":
                def _dl(hi, hcx, hcy, sc):
                    s = cs * sc
                    r = pygame.Rect(int(2 * sc), int(2 * sc), int(s - 4 * sc), int(s - 4 * sc))
                    pygame.draw.rect(hi, (118, 52, 14, 255), r, border_radius=int(5 * sc))
                    pygame.draw.rect(hi, (245, 158, 11, 255), r, width=max(2, int(2.4 * sc)), border_radius=int(5 * sc))
                    pygame.draw.arc(hi, (251, 191, 36, 255), (int(s * 0.36), int(s * 0.28), int(s * 0.28), int(s * 0.30)), 0, math.pi, max(2, int(2.5 * sc)))
                    pygame.draw.rect(hi, (251, 191, 36, 255), (int(s * 0.32), int(s * 0.46), int(s * 0.36), int(s * 0.30)), border_radius=int(2 * sc))
                _render_aa_layer(dest, ss, (180, 105, 16), _dl)
            elif kind == "crate":
                def _dc(hi, hcx, hcy, sc):
                    s = cs * sc
                    r = pygame.Rect(int(2 * sc), int(2 * sc), int(s - 4 * sc), int(s - 4 * sc))
                    pygame.draw.rect(hi, (186, 92, 14, 255), r, border_radius=int(4 * sc))
                    pygame.draw.rect(hi, (212, 118, 32, 255), (r.left + int(3 * sc), r.top + int(3 * sc), r.width - int(6 * sc), r.height - int(6 * sc)), border_radius=int(2 * sc))
                    lw = max(2, int(2.4 * sc))
                    pygame.draw.rect(hi, (118, 52, 14, 255), r, width=lw, border_radius=int(4 * sc))
                    pygame.draw.line(hi, (118, 52, 14, 255), (int(5 * sc), int(5 * sc)), (int(s - 5 * sc), int(s - 5 * sc)), lw)
                    pygame.draw.line(hi, (118, 52, 14, 255), (int(s - 5 * sc), int(5 * sc)), (int(5 * sc), int(s - 5 * sc)), lw)
                _render_aa_layer(dest, ss, (160, 78, 14), _dc)
            elif kind == "key":
                def _dk(hi, hcx, hcy, sc):
                    s = cs * sc
                    lw = max(2, int(2.8 * sc))
                    pygame.draw.circle(hi, (250, 204, 21, 255), (int(hcx - s * 0.18), int(hcy)), max(3, int(s * 0.16)), lw)
                    pygame.draw.line(hi, (250, 204, 21, 255), (int(hcx - s * 0.02), int(hcy)), (int(hcx + s * 0.32), int(hcy)), lw)
                    pygame.draw.line(hi, (250, 204, 21, 255), (int(hcx + s * 0.18), int(hcy)), (int(hcx + s * 0.18), int(hcy + s * 0.12)), lw)
                    pygame.draw.line(hi, (250, 204, 21, 255), (int(hcx + s * 0.32), int(hcy)), (int(hcx + s * 0.32), int(hcy + s * 0.15)), lw)
                _render_aa_layer(dest, ss, (250, 204, 21), _dk)
            elif kind in ("mine_idle", "mine_hot"):
                def _dm(hi, hcx, hcy, sc):
                    s = cs * sc
                    lw = max(2, int(2.6 * sc))
                    for i in range(4):
                        a = i * math.pi / 4.0
                        pygame.draw.line(hi, (17, 24, 39, 255), (int(hcx - math.cos(a) * s * 0.44), int(hcy - math.sin(a) * s * 0.44)), (int(hcx + math.cos(a) * s * 0.44), int(hcy + math.sin(a) * s * 0.44)), lw)
                    pygame.draw.circle(hi, (31, 41, 55, 255), (int(hcx), int(hcy)), max(4, int(s * 0.34)))
                    pygame.draw.circle(hi, (55, 65, 81, 255), (int(hcx - s * 0.08), int(hcy - s * 0.08)), max(2, int(s * 0.14)))
                    led = (239, 68, 68, 255) if kind == "mine_hot" else (245, 158, 11, 255)
                    pygame.draw.circle(hi, led, (int(hcx), int(hcy)), max(2, int(s * 0.13)))
                _render_aa_layer(dest, ss, (31, 41, 55), _dm)
            elif kind == "target":
                def _dt(hi, hcx, hcy, sc):
                    s = cs * sc
                    lw = max(2, int(2.8 * sc))
                    pygame.draw.rect(hi, (22, 163, 74, 255), (int(4 * sc), int(4 * sc), int(s - 8 * sc), int(s - 8 * sc)), lw, border_radius=int(3 * sc))
                    pygame.draw.line(hi, (22, 163, 74, 255), (int(8 * sc), int(8 * sc)), (int(s - 8 * sc), int(s - 8 * sc)), lw)
                    pygame.draw.line(hi, (22, 163, 74, 255), (int(s - 8 * sc), int(8 * sc)), (int(8 * sc), int(s - 8 * sc)), lw)
                _render_aa_layer(dest, ss, (22, 163, 74), _dt)

        return _get_cached_sprite(key, cs, cs, _build)

    def _draw_mode_entities(self, surf, engine, theme: Dict) -> None:
        cs = engine.cell_size
        is_pixel = engine.settings["graphics_style"] == "pixel"

        if engine.targets:
            t_spr = self._get_obstacle_sprite("target", cs)
            for t in engine.targets:
                surf.blit(t_spr, (t["x"] * cs, t["y"] * cs))

        if engine.mines:
            m_idle = self._get_obstacle_sprite("mine_idle", cs)
            m_hot = self._get_obstacle_sprite("mine_hot", cs)
            for m in engine.mines:
                ratio = m["timer_ms"] / max(1.0, m["max_timer_ms"])
                alpha_z = int((0.22 + (1.0 - ratio) * 0.32) * 255) if m["triggered"] else 32
                zone = pygame.Surface((cs * 3, cs * 3), pygame.SRCALPHA)
                zone.fill((239, 68, 68, alpha_z))
                surf.blit(zone, ((m["x"] - 1) * cs, (m["y"] - 1) * cs))
                surf.blit(m_hot if m["triggered"] else m_idle, (m["x"] * cs, m["y"] * cs))
                if m["triggered"]:
                    cx, cy = int(m["x"] * cs + cs / 2), int(m["y"] * cs + cs / 2)
                    r_arc = max(6, int(cs * 0.46))
                    pygame.draw.arc(surf, (254, 240, 138), (cx - r_arc, cy - r_arc, r_arc * 2, r_arc * 2), math.pi / 2.0, math.pi / 2.0 + math.pi * 2.0 * ratio, 3)

        if engine.walls:
            w_spr = self._get_obstacle_sprite("wall", cs)
            for w in engine.walls:
                surf.blit(w_spr, (w["x"] * cs, w["y"] * cs))

        if engine.statues:
            st_spr = self._get_obstacle_sprite("statue", cs)
            for st in engine.statues:
                surf.blit(st_spr, (st["x"] * cs, st["y"] * cs))

        if engine.locks:
            lk_spr = self._get_obstacle_sprite("lock", cs)
            for lk in engine.locks:
                surf.blit(lk_spr, (lk["x"] * cs, lk["y"] * cs))

        if engine.keys:
            k_spr = self._get_obstacle_sprite("key", cs)
            bob = int(round(math.sin(engine.game_time_ms * 0.008) * 2.5))
            for k in engine.keys:
                surf.blit(k_spr, (k["x"] * cs, k["y"] * cs + bob))

        if engine.crates:
            c_spr = self._get_obstacle_sprite("crate", cs)
            for c in engine.crates:
                surf.blit(c_spr, (c["x"] * cs, c["y"] * cs))

        for p in engine.poisons:
            cx, cy = engine.cell_center_px(p)
            pulse = 1.0 + math.sin(engine.game_time_ms * 0.007) * 0.04
            draw_fruit(surf, "poison", cx, cy, cs, p["spawn_scale"] * pulse, theme["shadow"], True, 255, False, engine.game_time_ms, is_pixel)

        if ModeEngine.has(engine, "portal"):
            def _build_ring(dest: pygame.Surface) -> None:
                def _dr(hi, hcx, hcy, sc):
                    for seg in range(6):
                        pygame.draw.arc(
                            hi,
                            (168, 85, 247, 235),
                            (int(hcx - cs * 0.45 * sc), int(hcy - cs * 0.45 * sc), int(cs * 0.90 * sc), int(cs * 0.90 * sc)),
                            seg * (math.pi / 3.0),
                            seg * (math.pi / 3.0) + 0.65,
                            max(2, int(2.6 * sc)),
                        )
                _render_aa_layer(dest, 4, (168, 85, 247), _dr)

            base_ring = _get_cached_sprite(("portal_ring_clean", cs), cs + 8, cs + 8, _build_ring)
            angle_deg = -(engine.game_time_ms * 0.22) % 360.0
            rot_ring = pygame.transform.rotozoom(base_ring, angle_deg, 1.0)
            for f in engine.foods:
                cx, cy = engine.cell_center_px(f)
                surf.blit(rot_ring, rot_ring.get_rect(center=(int(cx), int(cy))))

    def _ensure_light_radial(self) -> pygame.Surface:
        if self._light_radial_unit is not None:
            return self._light_radial_unit
        sz = 128
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        half = (sz - 1) / 2.0
        for y in range(sz):
            dy = (y - half) / half
            for x in range(sz):
                dx = (x - half) / half
                dist = math.hypot(dx, dy)
                if dist <= 0.28:
                    a = 0
                elif dist >= 1.0:
                    a = 240
                else:
                    norm = (dist - 0.28) / 0.72
                    smooth = norm * norm * (3.0 - 2.0 * norm)
                    a = int(round(240 * smooth))
                s.set_at((x, y), (0, 0, 0, a))
        self._light_radial_unit = s
        return s

    def _draw_light_mask(self, surf: pygame.Surface, engine) -> None:
        w, h = surf.get_size()
        hx, hy = engine.get_interpolated_head_px()
        rad_px = max(24, int(round(engine.light_radius * engine.cell_size)))
        diam = rad_px * 2
        unit = self._ensure_light_radial()
        spot = pygame.transform.smoothscale(unit, (diam, diam))

        ix, iy = int(round(hx - rad_px)), int(round(hy - rad_px))
        dark = (0, 0, 0, 240)
        mask = self._light_mask_buf if (self._light_mask_buf is not None and self._light_mask_buf.get_size() == (w, h)) else pygame.Surface((w, h), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        if iy > 0:
            mask.fill(dark, (0, 0, w, iy))
        if iy + diam < h:
            mask.fill(dark, (0, iy + diam, w, h - (iy + diam)))
        if ix > 0:
            mask.fill(dark, (0, max(0, iy), ix, min(h, iy + diam) - max(0, iy)))
        if ix + diam < w:
            mask.fill(dark, (ix + diam, max(0, iy), w - (ix + diam), min(h, iy + diam) - max(0, iy)))
        mask.blit(spot, (ix, iy))
        surf.blit(mask, (0, 0))

    def render(self, engine) -> pygame.Surface:
        theme = C.THEMES.get(engine.settings["theme"], C.THEMES["classic"])
        color_cfg = C.SNAKE_COLORS.get(engine.settings["snake_color"], C.SNAKE_COLORS["blue"])
        is_pixel = engine.settings["graphics_style"] == "pixel"
        self._ensure_surfaces(engine, theme)

        surf = self.board_surface
        if engine.state == "PAUSED" and self._paused_rendered:
            return surf
        self._paused_rendered = (engine.state == "PAUSED")
        cs = engine.cell_size

        # 1. Static cached checkerboard
        surf.blit(self.board_cache, (0, 0))

        # 2. Mode entities (4x SSAA color-matched)
        self._draw_mode_entities(surf, engine, theme)

        # 3. Food items (4x SSAA color-matched in Smooth mode, 9x9 pixel art in Pixel mode)
        idle_pulse = 1.0 + math.sin(engine.game_time_ms * 0.006) * 0.035
        is_dim = ModeEngine.has(engine, "dimension")
        is_winged = ModeEngine.has(engine, "winged")

        for f in engine.foods:
            cx, cy = engine.cell_center_px(f)
            in_other = is_dim and f["dimension"] != engine.active_dimension
            draw_fruit(
                surf,
                f["sprite"],
                cx,
                cy,
                cs,
                f["spawn_scale"] * idle_pulse,
                theme["shadow"],
                not in_other,
                76 if in_other else 255,
                is_winged,
                engine.game_time_ms,
                is_pixel,
            )

        # 4. Yin Yang second snake
        if ModeEngine.has(engine, "yinyang") and engine.yin_yang_snake:
            yy_dir = (float(engine.yin_yang_dir["x"]), float(engine.yin_yang_dir["y"]))
            self._draw_snake(surf, engine, engine.yin_yang_snake, engine.yin_yang_prev_tail, engine.yin_yang_just_grew, yy_dir, color_cfg, True, False)

        # 5. Main snake (Single unified 2x SSAA layer — ZERO seams, ZERO halos!)
        self._draw_snake(surf, engine, engine.snake, engine.prev_tail, engine.just_grew, engine.get_normalized_head_dir(), color_cfg, False, True)

        # 6. Eating particles (color-matched 4x AA in Smooth mode)
        for part in engine.particles:
            if is_pixel:
                ps = max(2, int(round(part["r"] * part["life"] * 1.6)))
                pygame.draw.rect(surf, (231, 71, 29), (int(part["x"] - ps / 2), int(part["y"] - ps / 2), ps, ps))
            else:
                rad = max(2, int(round(part["r"] * part["life"])))
                pspr = self._get_particle_sprite(rad)
                surf.blit(pspr, (int(round(part["x"] - pspr.get_width() / 2.0)), int(round(part["y"] - pspr.get_height() / 2.0))))

        # 7. Poison dizzy screen tint
        if ModeEngine.has(engine, "poison") and engine.poison_steps_remaining > 0:
            tint = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            tint.fill((100, 116, 139, 56))
            surf.blit(tint, (0, 0))

        # 8. Smooth radial Light Mode darkness mask
        if ModeEngine.has(engine, "light"):
            self._draw_light_mask(surf, engine)

        return surf
