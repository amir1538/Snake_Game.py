"""Snaky Game — Halo-Free Color-Matched 4x SSAA Vector Icons & Fruits.

Every supersampled layer is pre-filled with `(*layer_rgb, 0)` before downscaling
with `pygame.transform.smoothscale`. This completely eliminates Pygame's non-premultiplied
alpha dark-halo bug and produces smooth, crisp HTML5-Canvas-identical vector graphics.
"""

import math
from typing import Callable, Dict, Tuple

import pygame

from . import constants as C

_SPRITE_CACHE: Dict[Tuple, pygame.Surface] = {}
_MAX_CACHE_ENTRIES = 640


def clear_icon_cache() -> None:
    _SPRITE_CACHE.clear()


def _render_aa_layer(
    dest: pygame.Surface,
    ss: int,
    bg_rgb: Tuple[int, int, int],
    draw_fn: Callable[[pygame.Surface, float, float, float], None],
) -> None:
    """Renders one color-matched supersampled layer onto `dest` with ZERO dark halo."""
    w, h = dest.get_size()
    hi_w, hi_h = max(2, w * ss), max(2, h * ss)
    hi = pygame.Surface((hi_w, hi_h), pygame.SRCALPHA)
    hi.fill((bg_rgb[0], bg_rgb[1], bg_rgb[2], 0))
    draw_fn(hi, hi_w / 2.0, hi_h / 2.0, float(ss))
    down = pygame.transform.smoothscale(hi, (w, h))
    dest.blit(down, (0, 0))


def _get_cached_sprite(
    key: Tuple,
    out_w: int,
    out_h: int,
    build_fn: Callable[[pygame.Surface], None],
) -> pygame.Surface:
    surf = _SPRITE_CACHE.get(key)
    if surf is not None:
        return surf

    if len(_SPRITE_CACHE) >= _MAX_CACHE_ENTRIES:
        _SPRITE_CACHE.clear()

    surf = pygame.Surface((max(2, int(out_w)), max(2, int(out_h))), pygame.SRCALPHA)
    build_fn(surf)
    _SPRITE_CACHE[key] = surf
    return surf


def draw_rotated_ellipse(surface, color, cx: float, cy: float, rx: float, ry: float, angle_deg: float, steps: int = 36) -> None:
    if rx < 0.8 or ry < 0.8:
        return
    rad = math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    pts = []
    for i in range(steps):
        t = (2.0 * math.pi * i) / steps
        ex = rx * math.cos(t)
        ey = ry * math.sin(t)
        pts.append((int(round(cx + ex * ca - ey * sa)), int(round(cy + ex * sa + ey * ca))))
    pygame.draw.polygon(surface, color, pts)


def draw_rounded_rect_aa(
    surface: pygame.Surface,
    color: Tuple[int, ...],
    rect: pygame.Rect,
    radius: int,
    border_width: int = 0,
    border_color: Tuple[int, ...] = None,
) -> None:
    """Color-matched 3x SSAA rounded rectangle with zero dark corner halo."""
    w, h = max(2, int(rect.width)), max(2, int(rect.height))
    rgb = (color[0], color[1], color[2])
    alpha = color[3] if len(color) > 3 else 255
    key = ("rrect_clean", w, h, radius, rgb, alpha, border_width, border_color)

    def _build(dest: pygame.Surface) -> None:
        _render_aa_layer(
            dest,
            3,
            rgb,
            lambda hi, _cx, _cy, sc: pygame.draw.rect(
                hi, (*rgb, alpha), (0, 0, int(w * sc), int(h * sc)), border_radius=int(radius * sc)
            ),
        )
        if border_width > 0 and border_color is not None:
            brgb = (border_color[0], border_color[1], border_color[2])
            ba = border_color[3] if len(border_color) > 3 else 255
            _render_aa_layer(
                dest,
                3,
                brgb,
                lambda hi, _cx, _cy, sc: pygame.draw.rect(
                    hi,
                    (*brgb, ba),
                    (0, 0, int(w * sc), int(h * sc)),
                    width=max(1, int(border_width * sc)),
                    border_radius=int(radius * sc),
                ),
            )

    spr = _get_cached_sprite(key, w, h, _build)
    surface.blit(spr, rect.topleft)


def draw_pixel_fruit(
    surface,
    sprite: str,
    cx: float,
    cy: float,
    cell_size: float,
    scale: float,
    shadow_color: Tuple[int, int, int],
    has_shadow: bool = True,
    alpha: int = 255,
) -> None:
    """Crisp 9x9 pixel-art fruit for Pixel graphics style."""
    if scale <= 0.05:
        return
    u = max(2, int(round((cell_size / 11.0) * scale)))
    w_tot = 9 * u
    h_tot = 10 * u
    target = surface if alpha >= 255 else pygame.Surface((w_tot + 4, h_tot + 4), pygame.SRCALPHA)
    ox = int(round(cx - 4.5 * u)) if alpha >= 255 else 2
    oy = int(round(cy - 4.5 * u)) if alpha >= 255 else 2

    main_colors = {
        "apple": (231, 71, 29),
        "banana": (247, 201, 39),
        "pineapple": (234, 179, 8),
        "grapes": (139, 66, 217),
        "cherry": (217, 27, 66),
        "watermelon": (232, 56, 79),
        "strawberry": (242, 43, 63),
        "orange": (250, 139, 20),
        "poison": (100, 116, 139),
    }
    hl_colors = {
        "apple": (246, 132, 102),
        "banana": (255, 240, 138),
        "pineapple": (254, 240, 138),
        "grapes": (198, 149, 255),
        "cherry": (255, 143, 163),
        "watermelon": (82, 172, 42),
        "strawberry": (253, 224, 71),
        "orange": (255, 196, 107),
        "poison": (148, 163, 184),
    }
    body_col = main_colors.get(sprite, (231, 71, 29))
    hl_col = hl_colors.get(sprite, (246, 132, 102))

    def px(gx, gy, pw, ph, col):
        pygame.draw.rect(target, col, (ox + gx * u, oy + gy * u, pw * u, ph * u))

    if has_shadow:
        px(2, 9, 5, 1, shadow_color)

    px(5, 0, 3, 1, (82, 172, 42))
    px(5, 1, 2, 1, (82, 172, 42))
    px(4, 1, 1, 2, (118, 84, 46))

    px(2, 2, 5, 1, body_col)
    px(1, 3, 7, 4, body_col)
    px(2, 7, 5, 1, body_col)
    px(3, 8, 3, 1, body_col)

    px(2, 3, 2, 1, hl_col)
    px(2, 4, 1, 1, hl_col)

    if sprite == "poison":
        px(2, 5, 1, 1, (30, 41, 59))
        px(6, 5, 1, 1, (30, 41, 59))

    if alpha < 255:
        target.set_alpha(alpha)
        surface.blit(target, (int(round(cx - 4.5 * u)) - 2, int(round(cy - 4.5 * u)) - 2))


def _build_fruit_sprite_4x(dest: pygame.Surface, sprite: str, base_r: float) -> None:
    """Draws each color component of a fruit on its own color-matched 4x SSAA layer (ZERO dark halos!)."""
    ss = 4

    def oy(cy: float, sc: float) -> float:
        return cy + base_r * 0.12 * sc

    if sprite == "poison":
        # Stem
        _render_aa_layer(dest, ss, (71, 85, 105), lambda hi, cx, cy, sc: pygame.draw.line(
            hi, (71, 85, 105, 255), (int(cx), int(oy(cy, sc) - base_r * 0.78 * sc)), (int(cx), int(oy(cy, sc) - base_r * 1.25 * sc)), max(2, int(base_r * 0.18 * sc))
        ))
        # Gray poison body + highlight + eyes inside opaque body
        def _pbody(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            pygame.draw.ellipse(hi, (100, 116, 139, 255), (int(cx - r), int(cy2 - r * 0.94), int(r * 2), int(r * 1.88)))
            draw_rotated_ellipse(hi, (158, 174, 194, 255), cx - r * 0.34, cy2 - r * 0.30, r * 0.30, r * 0.16, -38)
            pygame.draw.circle(hi, (24, 34, 48, 255), (int(cx - r * 0.28), int(cy2 + r * 0.05)), max(2, int(r * 0.16)))
            pygame.draw.circle(hi, (24, 34, 48, 255), (int(cx + r * 0.28), int(cy2 + r * 0.05)), max(2, int(r * 0.16)))
        _render_aa_layer(dest, ss, (100, 116, 139), _pbody)

    elif sprite == "pineapple":
        # Green crown
        def _crown(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            for dx_off, top_y in ((-0.38, -1.15), (0.38, -1.15), (0.0, -1.48)):
                pygame.draw.polygon(hi, (78, 170, 40, 255), [
                    (int(cx + dx_off * r), int(cy2 + top_y * r)),
                    (int(cx - r * 0.34), int(cy2 - r * 0.60)),
                    (int(cx + r * 0.34), int(cy2 - r * 0.60)),
                ])
        _render_aa_layer(dest, ss, (78, 170, 40), _crown)

        # Golden body + crosshatch
        def _pinbody(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            pygame.draw.ellipse(hi, (234, 179, 8, 255), (int(cx - r * 0.78), int(cy2 - r * 0.78), int(r * 1.56), int(r * 1.84)))
            lw = max(2, int(r * 0.10))
            pygame.draw.line(hi, (194, 132, 4, 255), (int(cx - r * 0.44), int(cy2 - r * 0.34)), (int(cx + r * 0.44), int(cy2 + r * 0.54)), lw)
            pygame.draw.line(hi, (194, 132, 4, 255), (int(cx + r * 0.44), int(cy2 - r * 0.34)), (int(cx - r * 0.44), int(cy2 + r * 0.54)), lw)
            draw_rotated_ellipse(hi, (255, 238, 128, 255), cx - r * 0.28, cy2 - r * 0.24, r * 0.22, r * 0.12, -35)
        _render_aa_layer(dest, ss, (234, 179, 8), _pinbody)

    elif sprite == "banana":
        def _ban(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            pts = [(int(cx - r * 0.2 + math.cos(0.22 + math.pi * 0.64 * (i / 20.0)) * r * 0.90),
                    int(cy2 - r * 0.2 + math.sin(0.22 + math.pi * 0.64 * (i / 20.0)) * r * 0.90)) for i in range(21)]
            for px_i, py_i in pts:
                pygame.draw.circle(hi, (247, 201, 39, 255), (px_i, py_i), max(3, int(r * 0.30)))
            pygame.draw.lines(hi, (255, 242, 148, 255), False, pts[3:-3], max(2, int(r * 0.16)))
        _render_aa_layer(dest, ss, (247, 201, 39), _ban)

    elif sprite == "cherry":
        def _stems(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            lw = max(2, int(r * 0.15))
            pygame.draw.line(hi, (78, 162, 40, 255), (int(cx - r * 0.42), int(cy2 + r * 0.1)), (int(cx + r * 0.12), int(cy2 - r * 0.95)), lw)
            pygame.draw.line(hi, (78, 162, 40, 255), (int(cx + r * 0.42), int(cy2 + r * 0.2)), (int(cx + r * 0.12), int(cy2 - r * 0.95)), lw)
            draw_rotated_ellipse(hi, (82, 172, 42, 255), cx + r * 0.45, cy2 - r * 0.88, r * 0.38, r * 0.18, -18)
        _render_aa_layer(dest, ss, (82, 172, 42), _stems)

        def _cherries(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            for ox, oy_c in ((-0.42, 0.25), (0.42, 0.32)):
                pygame.draw.circle(hi, (217, 27, 66, 255), (int(cx + ox * r), int(cy2 + oy_c * r)), max(2, int(r * 0.52)))
                draw_rotated_ellipse(hi, (255, 160, 178, 255), cx + (ox - 0.18) * r, cy2 + (oy_c - 0.18) * r, r * 0.16, r * 0.10, -35)
        _render_aa_layer(dest, ss, (217, 27, 66), _cherries)

    elif sprite == "grapes":
        _render_aa_layer(dest, ss, (82, 172, 42), lambda hi, cx, cy, sc: draw_rotated_ellipse(
            hi, (82, 172, 42, 255), cx + base_r * 0.26 * sc, oy(cy, sc) - base_r * 0.78 * sc, base_r * 0.40 * sc, base_r * 0.19 * sc, -22
        ))
        def _grp(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            for ox, oy_g in ((-0.35, -0.3), (0.0, -0.3), (0.35, -0.3), (-0.22, 0.1), (0.22, 0.1), (0.0, 0.48)):
                pygame.draw.circle(hi, (139, 66, 217, 255), (int(cx + ox * r), int(cy2 + oy_g * r)), max(2, int(r * 0.36)))
                pygame.draw.circle(hi, (206, 164, 255, 255), (int(cx + (ox - 0.11) * r), int(cy2 + (oy_g - 0.11) * r)), max(1, int(r * 0.10)))
        _render_aa_layer(dest, ss, (139, 66, 217), _grp)

    elif sprite == "watermelon":
        def _wm(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            outer = [(int(cx + math.cos(a) * r), int(cy2 - r * 0.15 + math.sin(a) * r)) for a in [math.pi * i / 28 for i in range(29)]]
            rind = [(int(cx + math.cos(a) * r * 0.86), int(cy2 - r * 0.15 + math.sin(a) * r * 0.86)) for a in [math.pi * i / 28 for i in range(29)]]
            inner = [(int(cx + math.cos(a) * r * 0.78), int(cy2 - r * 0.15 + math.sin(a) * r * 0.78)) for a in [math.pi * i / 28 for i in range(29)]]
            pygame.draw.polygon(hi, (46, 139, 59, 255), outer)
            pygame.draw.polygon(hi, (224, 248, 214, 255), rind)
            pygame.draw.polygon(hi, (234, 58, 82, 255), inner)
            for sx in (-0.36, 0.0, 0.36):
                draw_rotated_ellipse(hi, (31, 41, 55, 255), cx + sx * r, cy2 + r * 0.22, r * 0.07, r * 0.11, sx * 25)
        _render_aa_layer(dest, ss, (46, 139, 59), _wm)

    elif sprite == "strawberry":
        def _sb(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            pts = [
                (int(cx), int(cy2 + r * 0.96)),
                (int(cx - r * 0.64), int(cy2 + r * 0.44)),
                (int(cx - r * 0.86), int(cy2 - r * 0.08)),
                (int(cx - r * 0.66), int(cy2 - r * 0.62)),
                (int(cx + r * 0.66), int(cy2 - r * 0.62)),
                (int(cx + r * 0.86), int(cy2 - r * 0.08)),
                (int(cx + r * 0.64), int(cy2 + r * 0.44)),
            ]
            pygame.draw.polygon(hi, (238, 40, 60, 255), pts)
            for sx, sy in ((-0.3, -0.1), (0.3, -0.1), (0.0, 0.25), (-0.2, 0.45), (0.2, 0.45)):
                pygame.draw.circle(hi, (253, 224, 71, 255), (int(cx + sx * r), int(cy2 + sy * r)), max(1, int(r * 0.09)))
        _render_aa_layer(dest, ss, (238, 40, 60), _sb)
        _render_aa_layer(dest, ss, (82, 172, 42), lambda hi, cx, cy, sc: draw_rotated_ellipse(
            hi, (82, 172, 42, 255), cx, oy(cy, sc) - base_r * 0.68 * sc, base_r * 0.52 * sc, base_r * 0.22 * sc, 0
        ))

    elif sprite == "orange":
        _render_aa_layer(dest, ss, (82, 172, 42), lambda hi, cx, cy, sc: draw_rotated_ellipse(
            hi, (82, 172, 42, 255), cx + base_r * 0.28 * sc, oy(cy, sc) - base_r * 0.88 * sc, base_r * 0.42 * sc, base_r * 0.20 * sc, -22
        ))
        def _org(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            pygame.draw.circle(hi, (250, 139, 20, 255), (int(cx), int(cy2)), int(r))
            draw_rotated_ellipse(hi, (255, 206, 124, 255), cx - r * 0.34, cy2 - r * 0.30, r * 0.32, r * 0.18, -35)
        _render_aa_layer(dest, ss, (250, 139, 20), _org)

    elif sprite == "random":
        def _rdice(hi, cx, cy, sc):
            sz = base_r * 1.85 * sc
            _draw_dice_hi(hi, cx, cy, sz, (255, 255, 255, 255), (17, 85, 204, 255), True)
        _render_aa_layer(dest, ss, (255, 255, 255), _rdice)

    else:
        # Default Apple — 3 clean color-matched 4x SSAA layers (ZERO dark halo, silky HTML5 Canvas look!)
        # Layer 1: Red apple body + warm soft gloss highlight
        def _apple_body(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            pygame.draw.ellipse(hi, (231, 71, 29, 255), (int(cx - r), int(cy2 - r * 0.95), int(r * 2.0), int(r * 1.90)))
            draw_rotated_ellipse(hi, (246, 132, 102, 255), cx - r * 0.36, cy2 - r * 0.30, r * 0.35, r * 0.19, -38)
        _render_aa_layer(dest, ss, (231, 71, 29), _apple_body)

        # Layer 2: Brown stem
        def _stem(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            w = max(2, int(r * 0.19))
            x = int(cx - r * 0.04)
            y1, y2 = int(cy2 - r * 0.78), int(cy2 - r * 1.24)
            pygame.draw.line(hi, (118, 84, 46, 255), (x, y1), (x, y2), w)
            pygame.draw.circle(hi, (118, 84, 46, 255), (x, y2), w // 2)
        _render_aa_layer(dest, ss, (118, 84, 46), _stem)

        # Layer 3: Crisp green leaf
        def _leaf(hi, cx, cy, sc):
            r = base_r * sc
            cy2 = oy(cy, sc)
            draw_rotated_ellipse(hi, (82, 172, 42, 255), cx + r * 0.42, cy2 - r * 1.06, r * 0.47, r * 0.23, -18)
        _render_aa_layer(dest, ss, (82, 172, 42), _leaf)


def draw_fruit(
    surface,
    sprite: str,
    cx: float,
    cy: float,
    cell_size: float,
    scale: float = 1.0,
    shadow_color: Tuple[int, int, int] = (130, 175, 55),
    has_shadow: bool = True,
    alpha: int = 255,
    is_winged: bool = False,
    game_time_ms: float = 0.0,
    is_pixel: bool = False,
) -> None:
    if is_pixel:
        draw_pixel_fruit(surface, sprite, cx, cy, cell_size, scale, shadow_color, has_shadow, alpha)
        return
    if scale <= 0.05:
        return

    r = max(2.0, (cell_size * 0.43) * scale)
    q_r = max(2.0, round(r * 2.0) / 2.0)
    box_sz = max(10, int(math.ceil(q_r * 3.3)) + 4)

    # Flapping white wings behind winged fruit (color-matched white AA)
    if is_winged:
        flap_step = int(round(math.sin(game_time_ms * 0.018) * 6.0)) * 4
        w_key = ("wings", int(round(q_r)), flap_step)

        def _build_wings(dest: pygame.Surface) -> None:
            def _dw(hi, hcx, hcy, sc):
                rr = q_r * sc
                for side in (-1, 1):
                    draw_rotated_ellipse(hi, (250, 252, 255, 240), hcx + side * rr * 1.05, hcy - rr * 0.06, rr * 0.62, rr * 0.28, side * (-20.0 + flap_step))
            _render_aa_layer(dest, 3, (250, 252, 255), _dw)

        w_box = max(16, int(math.ceil(q_r * 4.4)) + 4)
        w_spr = _get_cached_sprite(w_key, w_box, w_box, _build_wings)
        surface.blit(w_spr, (int(round(cx - w_box / 2.0)), int(round(cy - w_box / 2.0))))

    # Soft halo-free drop shadow (color-matched 4x SSAA)
    if has_shadow:
        sh_key = ("f_shadow_clean", box_sz, q_r, shadow_color)

        def _build_sh(dest: pygame.Surface) -> None:
            def _dsh(hi, hcx, hcy, sc):
                sr = q_r * sc
                pygame.draw.ellipse(
                    hi,
                    (*shadow_color, 180),
                    (int(hcx - sr * 0.90), int(hcy + sr * 0.42), int(sr * 1.80), int(sr * 0.78)),
                )
            _render_aa_layer(dest, 4, shadow_color, _dsh)

        sh_spr = _get_cached_sprite(sh_key, box_sz, box_sz, _build_sh)
        if alpha < 255:
            sh_copy = sh_spr.copy()
            sh_copy.set_alpha(alpha)
            surface.blit(sh_copy, (int(round(cx - box_sz / 2.0)), int(round(cy - box_sz / 2.0))))
        else:
            surface.blit(sh_spr, (int(round(cx - box_sz / 2.0)), int(round(cy - box_sz / 2.0))))

    key = ("fruit_clean4x", sprite, q_r)
    f_spr = _get_cached_sprite(key, box_sz, box_sz, lambda dest: _build_fruit_sprite_4x(dest, sprite, q_r))
    if alpha < 255:
        f_copy = f_spr.copy()
        f_copy.set_alpha(alpha)
        surface.blit(f_copy, (int(round(cx - box_sz / 2.0)), int(round(cy - box_sz / 2.0))))
    else:
        surface.blit(f_spr, (int(round(cx - box_sz / 2.0)), int(round(cy - box_sz / 2.0))))


def _draw_trophy_hi(surface: pygame.Surface, cx: float, cy: float, s: float) -> None:
    hl = pygame.Rect(int(cx - 18 * s), int(cy - 14 * s), int(12 * s), int(15 * s))
    hr = pygame.Rect(int(cx + 6 * s), int(cy - 14 * s), int(12 * s), int(15 * s))
    w_line = max(2, int(3.4 * s))
    pygame.draw.rect(surface, (*C.UI_GOLD, 255), hl, width=w_line, border_radius=max(2, int(5 * s)))
    pygame.draw.rect(surface, (*C.UI_GOLD, 255), hr, width=w_line, border_radius=max(2, int(5 * s)))
    cup = [
        (cx - 12 * s, cy - 16 * s),
        (cx + 12 * s, cy - 16 * s),
        (cx + 9 * s, cy + 2 * s),
        (cx - 9 * s, cy + 2 * s),
    ]
    pygame.draw.polygon(surface, (*C.UI_GOLD, 255), cup)
    pygame.draw.circle(surface, (*C.UI_GOLD, 255), (int(cx), int(cy - 2 * s)), max(2, int(9.2 * s)))
    hl_pts = [
        (cx - 9 * s, cy - 14 * s),
        (cx - 3 * s, cy - 14 * s),
        (cx - 3 * s, cy + 2 * s),
        (cx - 7 * s, cy - 1 * s),
    ]
    pygame.draw.polygon(surface, (*C.UI_GOLD_LIGHT, 255), hl_pts)
    pygame.draw.rect(surface, (*C.UI_GOLD_DARK, 255), (int(cx - 2.6 * s), int(cy + 5 * s), max(2, int(5.2 * s)), max(2, int(9 * s))))
    pygame.draw.rect(surface, (*C.UI_GOLD, 255), (int(cx - 9 * s), int(cy + 13 * s), max(4, int(18 * s)), max(2, int(4.5 * s))), border_radius=max(1, int(2 * s)))


def draw_trophy(surface, cx: float, cy: float, scale: float = 1.0) -> None:
    qs = round(scale, 2)
    box = max(16, int(math.ceil(44 * qs)))
    key = ("trophy_clean", qs)
    spr = _get_cached_sprite(
        key,
        box,
        box,
        lambda dest: _render_aa_layer(dest, 4, C.UI_GOLD, lambda hi, hcx, hcy, sc: _draw_trophy_hi(hi, hcx, hcy, qs * sc)),
    )
    surface.blit(spr, (int(round(cx - box / 2.0)), int(round(cy - box / 2.0))))


def _draw_dice_hi(surface: pygame.Surface, cx: float, cy: float, size: float, bg, dot, five: bool) -> None:
    rect = pygame.Rect(int(cx - size / 2), int(cy - size / 2), int(size), int(size))
    pygame.draw.rect(surface, bg, rect, border_radius=max(3, int(size * 0.18)))
    dr = max(2, int(size * 0.10))
    off = size * 0.23
    pygame.draw.circle(surface, dot, (int(cx), int(cy)), dr)
    pygame.draw.circle(surface, dot, (int(cx - off), int(cy - off)), dr)
    pygame.draw.circle(surface, dot, (int(cx + off), int(cy + off)), dr)
    if five:
        pygame.draw.circle(surface, dot, (int(cx + off), int(cy - off)), dr)
        pygame.draw.circle(surface, dot, (int(cx - off), int(cy + off)), dr)


def draw_dice_icon(surface, cx: float, cy: float, size: float = 24.0, bg=(255, 255, 255), dot=(17, 85, 204), five: bool = False) -> None:
    qsz = int(round(size))
    box = qsz + 6
    key = ("dice_clean", qsz, bg, dot, five)
    spr = _get_cached_sprite(
        key,
        box,
        box,
        lambda dest: _render_aa_layer(dest, 4, bg[:3], lambda hi, hcx, hcy, sc: _draw_dice_hi(hi, hcx, hcy, qsz * sc, (*bg[:3], 255), (*dot[:3], 255), five)),
    )
    surface.blit(spr, (int(round(cx - box / 2.0)), int(round(cy - box / 2.0))))


def draw_speaker_icon(surface, cx: int, cy: int, muted: bool) -> None:
    box = 34
    key = ("speaker_clean", muted)

    def _draw(hi: pygame.Surface, hcx: float, hcy: float, sc: float) -> None:
        pts = [
            (hcx - 9 * sc, hcy - 4 * sc),
            (hcx - 4 * sc, hcy - 4 * sc),
            (hcx + 2 * sc, hcy - 10 * sc),
            (hcx + 2 * sc, hcy + 10 * sc),
            (hcx - 4 * sc, hcy + 4 * sc),
            (hcx - 9 * sc, hcy + 4 * sc),
        ]
        pygame.draw.polygon(hi, (*C.UI_WHITE, 255), pts)
        if muted:
            w = max(2, int(2.4 * sc))
            pygame.draw.line(hi, (*C.UI_WHITE, 255), (hcx + 6 * sc, hcy - 5 * sc), (hcx + 13 * sc, hcy + 5 * sc), w)
            pygame.draw.line(hi, (*C.UI_WHITE, 255), (hcx + 6 * sc, hcy + 5 * sc), (hcx + 13 * sc, hcy - 5 * sc), w)
        else:
            w = max(2, int(2.0 * sc))
            pygame.draw.arc(hi, (*C.UI_WHITE, 255), (int(hcx + 1 * sc), int(hcy - 6 * sc), int(8 * sc), int(12 * sc)), -0.85, 0.85, w)
            pygame.draw.arc(hi, (*C.UI_WHITE, 255), (int(hcx + 3 * sc), int(hcy - 10 * sc), int(12 * sc), int(20 * sc)), -0.85, 0.85, w)

    spr = _get_cached_sprite(key, box, box, lambda dest: _render_aa_layer(dest, 4, C.UI_WHITE, _draw))
    surface.blit(spr, (cx - box // 2, cy - box // 2))


def draw_fullscreen_icon(surface, cx: int, cy: int, is_fs: bool) -> None:
    box = 28
    key = ("fullscreen_clean", is_fs)

    def _draw(hi: pygame.Surface, hcx: float, hcy: float, sc: float) -> None:
        d = 8 * sc
        l = 4.5 * sc
        w = max(2, int(2.2 * sc))
        if not is_fs:
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                x0, y0 = hcx + sx * d, hcy + sy * d
                pygame.draw.line(hi, (*C.UI_WHITE, 255), (x0, y0), (x0 - sx * l, y0), w)
                pygame.draw.line(hi, (*C.UI_WHITE, 255), (x0, y0), (x0, y0 - sy * l), w)
        else:
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                x0, y0 = hcx + sx * 3 * sc, hcy + sy * 3 * sc
                pygame.draw.line(hi, (*C.UI_WHITE, 255), (x0, y0), (x0 + sx * l, y0), w)
                pygame.draw.line(hi, (*C.UI_WHITE, 255), (x0, y0), (x0, y0 + sy * l), w)

    spr = _get_cached_sprite(key, box, box, lambda dest: _render_aa_layer(dest, 4, C.UI_WHITE, _draw))
    surface.blit(spr, (cx - box // 2, cy - box // 2))


def draw_gear_icon(surface, cx: int, cy: int, radius: int = 11, hole_color=(17, 85, 204), outline_only: bool = False) -> None:
    box = radius * 3 + 6
    key = ("gear_clean", radius, hole_color, outline_only)

    def _draw(hi: pygame.Surface, hcx: float, hcy: float, sc: float) -> None:
        r = radius * sc
        for i in range(8):
            ang = i * (math.pi / 4.0)
            x1 = hcx + math.cos(ang) * (r - 2 * sc)
            y1 = hcy + math.sin(ang) * (r - 2 * sc)
            x2 = hcx + math.cos(ang) * (r + 3.5 * sc)
            y2 = hcy + math.sin(ang) * (r + 3.5 * sc)
            pygame.draw.line(hi, (*C.UI_WHITE, 255), (int(x1), int(y1)), (int(x2), int(y2)), max(3, int(r * 0.36)))
        pygame.draw.circle(hi, (*C.UI_WHITE, 255), (int(hcx), int(hcy)), int(r))
        pygame.draw.circle(hi, (*hole_color[:3], 255), (int(hcx), int(hcy)), max(2, int(r * 0.52)))
        if outline_only:
            pygame.draw.circle(hi, (*C.UI_WHITE, 255), (int(hcx), int(hcy)), max(2, int(r * 0.45)), max(2, int(1.8 * sc)))

    spr = _get_cached_sprite(key, box, box, lambda dest: _render_aa_layer(dest, 4, C.UI_WHITE, _draw))
    surface.blit(spr, (cx - box // 2, cy - box // 2))


def draw_back_arrow(surface, cx: int, cy: int) -> None:
    box = 28
    key = ("back_arrow_clean",)

    def _draw(hi: pygame.Surface, hcx: float, hcy: float, sc: float) -> None:
        w = max(2, int(2.6 * sc))
        pygame.draw.line(hi, (*C.UI_WHITE, 255), (hcx - 7 * sc, hcy), (hcx + 8 * sc, hcy), w)
        pygame.draw.line(hi, (*C.UI_WHITE, 255), (hcx - 7 * sc, hcy), (hcx - 1 * sc, hcy - 6 * sc), w)
        pygame.draw.line(hi, (*C.UI_WHITE, 255), (hcx - 7 * sc, hcy), (hcx - 1 * sc, hcy + 6 * sc), w)

    spr = _get_cached_sprite(key, box, box, lambda dest: _render_aa_layer(dest, 4, C.UI_WHITE, _draw))
    surface.blit(spr, (cx - box // 2, cy - box // 2))


def draw_play_triangle(surface, cx: int, cy: int, size: int = 9) -> None:
    box = size * 3 + 6
    key = ("play_tri_clean", size)

    def _draw(hi: pygame.Surface, hcx: float, hcy: float, sc: float) -> None:
        sz = size * sc
        pts = [(hcx - sz + 2 * sc, hcy - sz), (hcx + sz, hcy), (hcx - sz + 2 * sc, hcy + sz)]
        pygame.draw.polygon(hi, (*C.UI_WHITE, 255), pts, width=max(2, int(2.2 * sc)))

    spr = _get_cached_sprite(key, box, box, lambda dest: _render_aa_layer(dest, 4, C.UI_WHITE, _draw))
    surface.blit(spr, (cx - box // 2, cy - box // 2))


# =========================================================================
# 8-Row Settings Carousel Icons (All Color-Matched 4x SSAA — Zero Halos!)
# =========================================================================
def _build_mode_icon(dest: pygame.Surface, mode_id: str, size: int) -> None:
    s0 = size / 28.0
    ss = 4

    if mode_id == "classic":
        _render_aa_layer(dest, ss, C.UI_GOLD, lambda hi, cx, cy, sc: _draw_trophy_hi(hi, cx, cy, 0.72 * s0 * sc))
    elif mode_id == "wall":
        def _w(hi, cx, cy, sc):
            s = s0 * sc
            r = pygame.Rect(int(cx - 11 * s), int(cy - 9 * s), int(22 * s), int(18 * s))
            pygame.draw.rect(hi, (107, 158, 91, 255), r, border_radius=max(2, int(2 * s)))
            lw = max(2, int(1.6 * s))
            pygame.draw.line(hi, (*C.UI_CARD_SKY, 255), (r.left, r.top + r.height // 3), (r.right, r.top + r.height // 3), lw)
            pygame.draw.line(hi, (*C.UI_CARD_SKY, 255), (r.left, r.top + (2 * r.height) // 3), (r.right, r.top + (2 * r.height) // 3), lw)
            pygame.draw.line(hi, (*C.UI_CARD_SKY, 255), (r.centerx, r.top), (r.centerx, r.top + r.height // 3), lw)
            pygame.draw.line(hi, (*C.UI_CARD_SKY, 255), (r.left + r.width // 3, r.top + r.height // 3), (r.left + r.width // 3, r.top + (2 * r.height) // 3), lw)
            pygame.draw.line(hi, (*C.UI_CARD_SKY, 255), (r.left + (2 * r.width) // 3, r.top + r.height // 3), (r.left + (2 * r.width) // 3, r.top + (2 * r.height) // 3), lw)
            pygame.draw.line(hi, (*C.UI_CARD_SKY, 255), (r.centerx, r.top + (2 * r.height) // 3), (r.centerx, r.bottom), lw)
        _render_aa_layer(dest, ss, (107, 158, 91), _w)
    elif mode_id == "portal":
        _render_aa_layer(dest, ss, (124, 58, 237), lambda hi, cx, cy, sc: pygame.draw.ellipse(
            hi, (124, 58, 237, 255), (int(cx - 11 * s0 * sc), int(cy - 9 * s0 * sc), int(9 * s0 * sc), int(18 * s0 * sc)), max(2, int(2.8 * s0 * sc))
        ))
        def _psn(hi, cx, cy, sc):
            s = s0 * sc
            pygame.draw.rect(hi, (79, 120, 248, 255), (int(cx - 5 * s), int(cy - 5 * s), int(15 * s), int(10 * s)), border_radius=max(2, int(5 * s)))
            pygame.draw.circle(hi, (255, 255, 255, 255), (int(cx + 3 * s), int(cy - 4 * s)), max(2, int(3 * s)))
            pygame.draw.circle(hi, (17, 63, 167, 255), (int(cx + 4 * s), int(cy - 4 * s)), max(1, int(1.5 * s)))
        _render_aa_layer(dest, ss, (79, 120, 248), _psn)
    elif mode_id == "cheese":
        def _ch(hi, cx, cy, sc):
            s = s0 * sc
            pts = [(int(cx - 11 * s), int(cy + 6 * s)), (int(cx + 11 * s), int(cy + 6 * s)), (int(cx + 9 * s), int(cy - 5 * s)), (int(cx - 11 * s), int(cy))]
            pygame.draw.polygon(hi, (234, 179, 8, 255), pts)
            pygame.draw.circle(hi, (161, 98, 7, 255), (int(cx - 3 * s), int(cy + 2 * s)), max(1, int(2.2 * s)))
            pygame.draw.circle(hi, (161, 98, 7, 255), (int(cx + 5 * s), int(cy + 1 * s)), max(1, int(2.4 * s)))
        _render_aa_layer(dest, ss, (234, 179, 8), _ch)
    elif mode_id == "noborders":
        def _nb(hi, cx, cy, sc):
            s = s0 * sc
            lw = max(2, int(2.4 * s))
            pygame.draw.circle(hi, (255, 255, 255, 255), (int(cx - 5 * s), int(cy)), max(3, int(5 * s)), lw)
            pygame.draw.circle(hi, (255, 255, 255, 255), (int(cx + 5 * s), int(cy)), max(3, int(5 * s)), lw)
        _render_aa_layer(dest, ss, C.UI_WHITE, _nb)
    elif mode_id == "twin":
        def _t1(hi, cx, cy, sc):
            s = s0 * sc
            lw = max(2, int(2.2 * s))
            pygame.draw.line(hi, (255, 255, 255, 255), (int(cx - 8 * s), int(cy - 4 * s)), (int(cx + 8 * s), int(cy - 4 * s)), lw)
            pygame.draw.line(hi, (255, 255, 255, 255), (int(cx + 4 * s), int(cy - 8 * s)), (int(cx + 8 * s), int(cy - 4 * s)), lw)
        def _t2(hi, cx, cy, sc):
            s = s0 * sc
            lw = max(2, int(2.2 * s))
            pygame.draw.line(hi, (253, 224, 71, 255), (int(cx + 8 * s), int(cy + 4 * s)), (int(cx - 8 * s), int(cy + 4 * s)), lw)
            pygame.draw.line(hi, (253, 224, 71, 255), (int(cx - 4 * s), int(cy + 8 * s)), (int(cx - 8 * s), int(cy + 4 * s)), lw)
        _render_aa_layer(dest, ss, C.UI_WHITE, _t1)
        _render_aa_layer(dest, ss, (253, 224, 71), _t2)
    elif mode_id == "winged":
        def _wg(hi, cx, cy, sc):
            s = s0 * sc
            draw_rotated_ellipse(hi, (255, 255, 255, 255), cx - 8 * s, cy - 1 * s, 5 * s, 2.5 * s, -20)
            draw_rotated_ellipse(hi, (255, 255, 255, 255), cx + 8 * s, cy - 1 * s, 5 * s, 2.5 * s, 20)
        _render_aa_layer(dest, ss, C.UI_WHITE, _wg)
        _render_aa_layer(dest, ss, (231, 71, 29), lambda hi, cx, cy, sc: pygame.draw.circle(hi, (231, 71, 29, 255), (int(cx), int(cy + 2 * s0 * sc)), max(3, int(6 * s0 * sc))))
    elif mode_id == "yinyang":
        def _yy(hi, cx, cy, sc):
            rad = max(5, int(10 * s0 * sc))
            pygame.draw.circle(hi, (255, 255, 255, 255), (int(cx), int(cy)), rad)
            pts = [(int(cx), int(cy - rad))] + [(int(cx + math.cos(-math.pi / 2.0 + math.pi * i / 20.0) * rad), int(cy + math.sin(-math.pi / 2.0 + math.pi * i / 20.0) * rad)) for i in range(21)]
            pygame.draw.polygon(hi, (30, 41, 59, 255), pts)
            pygame.draw.circle(hi, (30, 41, 59, 255), (int(cx), int(cy - rad // 2)), rad // 2)
            pygame.draw.circle(hi, (255, 255, 255, 255), (int(cx), int(cy + rad // 2)), rad // 2)
            pygame.draw.circle(hi, (255, 255, 255, 255), (int(cx), int(cy - rad // 2)), max(1, rad // 5))
            pygame.draw.circle(hi, (30, 41, 59, 255), (int(cx), int(cy + rad // 2)), max(1, rad // 5))
        _render_aa_layer(dest, ss, (160, 175, 195), _yy)
    elif mode_id == "key":
        def _ky(hi, cx, cy, sc):
            s = s0 * sc
            lw = max(2, int(2.6 * s))
            pygame.draw.circle(hi, (*C.UI_GOLD, 255), (int(cx - 5 * s), int(cy)), max(3, int(4.5 * s)), lw)
            pygame.draw.line(hi, (*C.UI_GOLD, 255), (int(cx - 1 * s), int(cy)), (int(cx + 10 * s), int(cy)), lw)
            pygame.draw.line(hi, (*C.UI_GOLD, 255), (int(cx + 6 * s), int(cy)), (int(cx + 6 * s), int(cy + 4 * s)), lw)
            pygame.draw.line(hi, (*C.UI_GOLD, 255), (int(cx + 10 * s), int(cy)), (int(cx + 10 * s), int(cy + 4 * s)), lw)
        _render_aa_layer(dest, ss, C.UI_GOLD, _ky)
    elif mode_id == "sokoban":
        def _sk(hi, cx, cy, sc):
            s = s0 * sc
            r = pygame.Rect(int(cx - 9 * s), int(cy - 9 * s), int(18 * s), int(18 * s))
            lw = max(2, int(2.0 * s))
            pygame.draw.rect(hi, (180, 83, 9, 255), r, border_radius=max(2, int(3 * s)))
            pygame.draw.rect(hi, (120, 53, 15, 255), r, width=lw, border_radius=max(2, int(3 * s)))
            pygame.draw.line(hi, (120, 53, 15, 255), r.topleft, r.bottomright, lw)
            pygame.draw.line(hi, (120, 53, 15, 255), r.topright, r.bottomleft, lw)
        _render_aa_layer(dest, ss, (180, 83, 9), _sk)
    elif mode_id == "poison":
        def _po(hi, cx, cy, sc):
            s = s0 * sc
            pygame.draw.circle(hi, (100, 116, 139, 255), (int(cx), int(cy + 2 * s)), max(4, int(8 * s)))
            pygame.draw.circle(hi, (15, 23, 42, 255), (int(cx - 3 * s), int(cy + 2 * s)), max(1, int(1.6 * s)))
            pygame.draw.circle(hi, (15, 23, 42, 255), (int(cx + 3 * s), int(cy + 2 * s)), max(1, int(1.6 * s)))
        _render_aa_layer(dest, ss, (100, 116, 139), _po)
    elif mode_id == "dimension":
        _render_aa_layer(dest, ss, (231, 71, 29), lambda hi, cx, cy, sc: pygame.draw.circle(hi, (231, 71, 29, 255), (int(cx - 3 * s0 * sc), int(cy)), max(3, int(6.5 * s0 * sc))))
        def _d2(hi, cx, cy, sc):
            s = s0 * sc
            pygame.draw.circle(hi, (147, 51, 234, 255), (int(cx + 3 * s), int(cy)), max(3, int(6.5 * s)))
            pygame.draw.circle(hi, (255, 255, 255, 255), (int(cx + 3 * s), int(cy)), max(3, int(6.5 * s)), max(1, int(1.4 * s)))
        _render_aa_layer(dest, ss, (147, 51, 234), _d2)
    elif mode_id == "minesweeper":
        def _ms(hi, cx, cy, sc):
            s = s0 * sc
            rad = max(4, int(6.5 * s))
            lw = max(2, int(2.2 * s))
            for i in range(4):
                a = i * math.pi / 4.0
                pygame.draw.line(hi, (31, 41, 55, 255), (int(cx - math.cos(a) * 10 * s), int(cy - math.sin(a) * 10 * s)), (int(cx + math.cos(a) * 10 * s), int(cy + math.sin(a) * 10 * s)), lw)
            pygame.draw.circle(hi, (31, 41, 55, 255), (int(cx), int(cy)), rad)
            pygame.draw.circle(hi, (239, 68, 68, 255), (int(cx), int(cy)), max(2, int(2.4 * s)))
        _render_aa_layer(dest, ss, (31, 41, 55), _ms)
    elif mode_id == "statue":
        def _st(hi, cx, cy, sc):
            s = s0 * sc
            r = pygame.Rect(int(cx - 8 * s), int(cy - 10 * s), int(16 * s), int(20 * s))
            lw = max(2, int(2.0 * s))
            pygame.draw.rect(hi, (148, 163, 184, 255), r, border_radius=max(2, int(3 * s)))
            pygame.draw.rect(hi, (71, 85, 105, 255), r, width=lw, border_radius=max(2, int(3 * s)))
            pygame.draw.lines(hi, (51, 65, 85, 255), False, [(int(cx - 2 * s), int(cy - 5 * s)), (int(cx + 2 * s), int(cy)), (int(cx - 1 * s), int(cy + 6 * s))], lw)
        _render_aa_layer(dest, ss, (148, 163, 184), _st)
    elif mode_id == "light":
        _render_aa_layer(dest, ss, (254, 240, 138), lambda hi, cx, cy, sc: pygame.draw.circle(hi, (254, 240, 138, 255), (int(cx), int(cy - 2 * s0 * sc)), max(3, int(6 * s0 * sc))))
        _render_aa_layer(dest, ss, (226, 232, 240), lambda hi, cx, cy, sc: pygame.draw.rect(hi, (226, 232, 240, 255), (int(cx - 3 * s0 * sc), int(cy + 4 * s0 * sc), int(6 * s0 * sc), int(4 * s0 * sc)), border_radius=max(1, int(1.2 * s0 * sc))))
    elif mode_id == "peace":
        def _pc(hi, cx, cy, sc):
            s = s0 * sc
            rad = max(5, int(9 * s))
            lw = max(2, int(2.2 * s))
            pygame.draw.circle(hi, (255, 255, 255, 255), (int(cx), int(cy)), rad, lw)
            pygame.draw.line(hi, (255, 255, 255, 255), (int(cx), int(cy - rad)), (int(cx), int(cy + rad)), lw)
            pygame.draw.line(hi, (255, 255, 255, 255), (int(cx), int(cy)), (int(cx - rad * 0.7), int(cy + rad * 0.7)), lw)
            pygame.draw.line(hi, (255, 255, 255, 255), (int(cx), int(cy)), (int(cx + rad * 0.7), int(cy + rad * 0.7)), lw)
        _render_aa_layer(dest, ss, C.UI_WHITE, _pc)
    elif mode_id == "blender":
        def _bl(hi, cx, cy, sc):
            s = s0 * sc
            pts = [(int(cx - 7 * s), int(cy - 9 * s)), (int(cx + 7 * s), int(cy - 9 * s)), (int(cx + 5 * s), int(cy + 5 * s)), (int(cx - 5 * s), int(cy + 5 * s))]
            pygame.draw.polygon(hi, (255, 255, 255, 255), pts)
            lw = max(2, int(2.2 * s))
            pygame.draw.line(hi, (*C.UI_BTN_BLUE, 255), (int(cx - 3 * s), int(cy - 4 * s)), (int(cx + 3 * s), int(cy + 2 * s)), lw)
            pygame.draw.line(hi, (*C.UI_BTN_BLUE, 255), (int(cx + 3 * s), int(cy - 4 * s)), (int(cx - 3 * s), int(cy + 2 * s)), lw)
        _render_aa_layer(dest, ss, C.UI_WHITE, _bl)
        _render_aa_layer(dest, ss, C.UI_GOLD, lambda hi, cx, cy, sc: pygame.draw.rect(hi, (*C.UI_GOLD, 255), (int(cx - 5 * s0 * sc), int(cy + 5 * s0 * sc), int(10 * s0 * sc), int(4 * s0 * sc)), border_radius=max(1, int(1.5 * s0 * sc))))


def draw_mode_icon(surface, mode_id: str, cx: int, cy: int, size: int = 26) -> None:
    box = size + 6
    key = ("mode_clean", mode_id, size)
    spr = _get_cached_sprite(key, box, box, lambda dest: _build_mode_icon(dest, mode_id, size))
    surface.blit(spr, (cx - box // 2, cy - box // 2))


def draw_count_icon(surface, count_id: str, cx: int, cy: int, is_selected: bool) -> None:
    if count_id == "dice":
        draw_dice_icon(surface, cx, cy, 22.0, five=True)
        return
    box = 30
    key = ("count_clean", count_id, is_selected)
    col = (231, 71, 29) if is_selected else (127, 107, 122)

    def _draw(hi: pygame.Surface, hcx: float, hcy: float, sc: float) -> None:
        if count_id == "1":
            pygame.draw.circle(hi, (*col, 255), (int(hcx), int(hcy)), int(10 * sc))
        elif count_id == "3":
            pygame.draw.circle(hi, (*col, 255), (int(hcx), int(hcy - 5.5 * sc)), int(5 * sc))
            pygame.draw.circle(hi, (*col, 255), (int(hcx - 5.5 * sc), int(hcy + 4.8 * sc)), int(5 * sc))
            pygame.draw.circle(hi, (*col, 255), (int(hcx + 5.5 * sc), int(hcy + 4.8 * sc)), int(5 * sc))
        elif count_id == "5":
            for ox, oy in ((-6, -6), (6, -6), (0, 0), (-6, 6), (6, 6)):
                pygame.draw.circle(hi, (*col, 255), (int(hcx + ox * sc), int(hcy + oy * sc)), int(4 * sc))

    spr = _get_cached_sprite(key, box, box, lambda dest: _render_aa_layer(dest, 4, col, _draw))
    surface.blit(spr, (cx - box // 2, cy - box // 2))


def draw_speed_icon(surface, speed_id: str, cx: int, cy: int) -> None:
    box = 32
    key = ("speed_clean", speed_id)

    def _build(dest: pygame.Surface) -> None:
        if speed_id == "rabbit":
            def _rb(hi, hcx, hcy, sc):
                pygame.draw.ellipse(hi, (226, 232, 240, 255), (int(hcx - 9 * sc), int(hcy - 1 * sc), int(14 * sc), int(10 * sc)))
                pygame.draw.circle(hi, (226, 232, 240, 255), (int(hcx + 5 * sc), int(hcy - 1 * sc)), int(4.2 * sc))
                pygame.draw.ellipse(hi, (226, 232, 240, 255), (int(hcx + 2 * sc), int(hcy - 11 * sc), int(3.2 * sc), int(9 * sc)))
                pygame.draw.ellipse(hi, (226, 232, 240, 255), (int(hcx + 6 * sc), int(hcy - 10 * sc), int(3.2 * sc), int(9 * sc)))
                pygame.draw.circle(hi, (30, 41, 59, 255), (int(hcx + 6 * sc), int(hcy - 2 * sc)), max(1, int(1.2 * sc)))
            _render_aa_layer(dest, 4, (226, 232, 240), _rb)
        elif speed_id == "turtle":
            def _tt(hi, hcx, hcy, sc):
                pygame.draw.ellipse(hi, (77, 158, 107, 255), (int(hcx - 10 * sc), int(hcy - 7 * sc), int(18 * sc), int(13 * sc)))
                pygame.draw.circle(hi, (107, 191, 138, 255), (int(hcx + 10 * sc), int(hcy + 1 * sc)), int(3.2 * sc))
                pygame.draw.rect(hi, (107, 191, 138, 255), (int(hcx - 7 * sc), int(hcy + 4 * sc), int(3 * sc), int(4 * sc)), border_radius=int(1 * sc))
                pygame.draw.rect(hi, (107, 191, 138, 255), (int(hcx + 3 * sc), int(hcy + 4 * sc), int(3 * sc), int(4 * sc)), border_radius=int(1 * sc))
            _render_aa_layer(dest, 4, (85, 168, 118), _tt)
        else:
            _render_aa_layer(dest, 4, (231, 71, 29), lambda hi, hcx, hcy, sc: pygame.draw.line(hi, (231, 71, 29, 255), (int(hcx - 11 * sc), int(hcy - 4 * sc)), (int(hcx - 7 * sc), int(hcy - 6 * sc)), max(2, int(1.8 * sc))))
            def _sn(hi, hcx, hcy, sc):
                pts = [
                    (int(hcx - 6 * sc), int(hcy - 6 * sc)),
                    (int(hcx), int(hcy - 7 * sc)),
                    (int(hcx + 2 * sc), int(hcy - 2 * sc)),
                    (int(hcx - 3 * sc), int(hcy + 3 * sc)),
                    (int(hcx + 2 * sc), int(hcy + 7 * sc)),
                    (int(hcx + 9 * sc), int(hcy + 5 * sc)),
                ]
                pygame.draw.lines(hi, (79, 120, 248, 255), False, pts, max(3, int(4.2 * sc)))
                for p_i in pts:
                    pygame.draw.circle(hi, (79, 120, 248, 255), p_i, max(2, int(2.1 * sc)))
                pygame.draw.circle(hi, (255, 255, 255, 255), (int(hcx - 5 * sc), int(hcy - 6 * sc)), max(2, int(2.2 * sc)))
                pygame.draw.circle(hi, (17, 63, 167, 255), (int(hcx - 5 * sc), int(hcy - 6 * sc)), max(1, int(1.1 * sc)))
            _render_aa_layer(dest, 4, (79, 120, 248), _sn)

    spr = _get_cached_sprite(key, box, box, _build)
    surface.blit(spr, (cx - box // 2, cy - box // 2))


def draw_board_size_icon(surface, size_id: str, cx: int, cy: int) -> None:
    box = 32
    key = ("board_sz_clean", size_id)

    def _draw(hi: pygame.Surface, hcx: float, hcy: float, sc: float) -> None:
        dim = (18 if size_id == "small" else (26 if size_id == "big" else 22)) * sc
        n = 2 if size_id == "small" else (4 if size_id == "big" else 3)
        step = dim / n
        ox = hcx - dim / 2.0
        oy = hcy - dim / 2.0
        for r in range(n):
            for c in range(n):
                col = (170, 215, 81, 255) if (r + c) % 2 == 0 else (142, 204, 58, 255)
                pygame.draw.rect(hi, col, (int(ox + c * step), int(oy + r * step), int(math.ceil(step)), int(math.ceil(step))))
        pygame.draw.rect(hi, (74, 117, 44, 255), (int(ox), int(oy), int(dim), int(dim)), max(2, int(1.8 * sc)))

    spr = _get_cached_sprite(key, box, box, lambda dest: _render_aa_layer(dest, 4, (74, 117, 44), _draw))
    surface.blit(spr, (cx - box // 2, cy - box // 2))


def draw_snake_ring_icon(surface, color_cfg: dict, cx: int, cy: int) -> None:
    box = 32
    key = ("snake_ring_clean", color_cfg["id"])
    body = color_cfg["head"]
    pupil = color_cfg["pupil"]

    def _draw(hi: pygame.Surface, hcx: float, hcy: float, sc: float) -> None:
        pygame.draw.circle(hi, (*body, 255), (int(hcx), int(hcy + 1 * sc)), int(10 * sc), max(3, int(4.4 * sc)))
        pygame.draw.circle(hi, (*body, 255), (int(hcx - 4 * sc), int(hcy - 8 * sc)), int(4 * sc))
        pygame.draw.circle(hi, (255, 255, 255, 255), (int(hcx - 4 * sc), int(hcy - 8 * sc)), int(2.2 * sc))
        pygame.draw.circle(hi, (*pupil, 255), (int(hcx - 4.8 * sc), int(hcy - 8 * sc)), int(1.2 * sc))

    spr = _get_cached_sprite(key, box, box, lambda dest: _render_aa_layer(dest, 4, body, _draw))
    surface.blit(spr, (cx - box // 2, cy - box // 2))


def draw_theme_icon(surface, theme_id: str, cx: int, cy: int) -> None:
    box = 32
    key = ("theme_ico_clean", theme_id)

    def _build(dest: pygame.Surface) -> None:
        if theme_id == "night":
            def _nt(hi, hcx, hcy, sc):
                pygame.draw.circle(hi, (217, 232, 156, 255), (int(hcx), int(hcy)), int(10 * sc))
                pygame.draw.circle(hi, (71, 107, 133, 255), (int(hcx + 4 * sc), int(hcy - 2 * sc)), int(8 * sc))
            _render_aa_layer(dest, 4, (180, 200, 150), _nt)
        elif theme_id == "winter":
            def _wt(hi, hcx, hcy, sc):
                lw = max(2, int(2.2 * sc))
                for i in range(3):
                    a = i * (math.pi / 3.0)
                    pygame.draw.line(hi, (224, 242, 254, 255), (int(hcx - math.cos(a) * 10 * sc), int(hcy - math.sin(a) * 10 * sc)), (int(hcx + math.cos(a) * 10 * sc), int(hcy + math.sin(a) * 10 * sc)), lw)
            _render_aa_layer(dest, 4, (224, 242, 254), _wt)
        elif theme_id == "volcano":
            def _vc(hi, hcx, hcy, sc):
                pygame.draw.polygon(hi, (92, 100, 107, 255), [(int(hcx - 10 * sc), int(hcy + 9 * sc)), (int(hcx - 4 * sc), int(hcy - 7 * sc)), (int(hcx + 4 * sc), int(hcy - 7 * sc)), (int(hcx + 10 * sc), int(hcy + 9 * sc))])
                pygame.draw.polygon(hi, (234, 88, 12, 255), [(int(hcx - 4 * sc), int(hcy - 7 * sc)), (int(hcx + 4 * sc), int(hcy - 7 * sc)), (int(hcx + 5 * sc), int(hcy - 2 * sc)), (int(hcx), int(hcy - 4 * sc)), (int(hcx - 5 * sc), int(hcy - 2 * sc))])
            _render_aa_layer(dest, 4, (92, 100, 107), _vc)
        else:
            def _dy(hi, hcx, hcy, sc):
                lw = max(2, int(2.2 * sc))
                for i in range(8):
                    a = i * (math.pi / 4.0)
                    pygame.draw.line(hi, (245, 158, 11, 255), (int(hcx), int(hcy)), (int(hcx + math.cos(a) * 12 * sc), int(hcy + math.sin(a) * 12 * sc)), lw)
                pygame.draw.circle(hi, (250, 204, 21, 255), (int(hcx), int(hcy)), int(7 * sc))
            _render_aa_layer(dest, 4, (248, 180, 16), _dy)

    spr = _get_cached_sprite(key, box, box, _build)
    surface.blit(spr, (cx - box // 2, cy - box // 2))


def draw_graphics_style_icon(surface, style_id: str, cx: int, cy: int) -> None:
    box = 36
    key = ("gstyle_clean", style_id)

    def _draw(hi: pygame.Surface, hcx: float, hcy: float, sc: float) -> None:
        if style_id == "pixel":
            for sx in (-7, 6):
                pygame.draw.rect(hi, (79, 120, 248, 255), (int(hcx + (sx - 5) * sc), int(hcy - 7 * sc), int(11 * sc), int(14 * sc)))
                pygame.draw.rect(hi, (255, 255, 255, 255), (int(hcx + (sx - 3) * sc), int(hcy - 5 * sc), int(7 * sc), int(10 * sc)))
                pygame.draw.rect(hi, (17, 63, 167, 255), (int(hcx + (sx - 3) * sc), int(hcy - 5 * sc), int(4 * sc), int(5 * sc)))
        else:
            for sx in (-7, 7):
                pygame.draw.circle(hi, (79, 120, 248, 255), (int(hcx + sx * sc), int(hcy)), int(7 * sc))
                pygame.draw.circle(hi, (255, 255, 255, 255), (int(hcx + sx * sc), int(hcy)), int(5 * sc))
                pygame.draw.circle(hi, (17, 63, 167, 255), (int(hcx + (sx - 1) * sc), int(hcy - 1 * sc)), int(3 * sc))

    spr = _get_cached_sprite(key, box, box, lambda dest: _render_aa_layer(dest, 4, (79, 120, 248), _draw))
    surface.blit(spr, (cx - box // 2, cy - box // 2))
