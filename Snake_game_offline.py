import ctypes
import io
import json
import math
import os
import random
import struct
import sys
import wave
import pygame

# راه‌اندازی صدای بازی
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.set_num_channels(16)

# ابعاد استاندارد صفحه
GRID_SIZE = 32
GRID_WIDTH = 17
GRID_HEIGHT = 15
TOP_BAR_HEIGHT = 60
BORDER_SIZE = 24

SCREEN_WIDTH = (GRID_WIDTH * GRID_SIZE) + (BORDER_SIZE * 2)
SCREEN_HEIGHT = (GRID_HEIGHT * GRID_SIZE) + TOP_BAR_HEIGHT + (BORDER_SIZE * 2)

# ==========================================
# پالت رنگی شاداب و پررنگ (Vibrant Game Snake Palette)
# ==========================================
COLOR_TOP_BAR = (74, 117, 44)
COLOR_BORDER = (87, 138, 52)
COLOR_LIGHT_GREEN = (170, 215, 81)
COLOR_DARK_GREEN = (162, 209, 73)
COLOR_SHADOW = (130, 175, 55)

COLOR_SNAKE_HEAD = (78, 124, 246)
COLOR_SNAKE_TAIL = (62, 104, 230)
COLOR_SNAKE_OUTLINE = (60, 102, 224)
COLOR_MOUTH_INSIDE = (24, 54, 142)
COLOR_PUPIL = (24, 52, 138)
COLOR_TONGUE = (235, 65, 25)

COLOR_APPLE = (234, 62, 24)
COLOR_APPLE_HIGHLIGHT = (246, 132, 102)
COLOR_LEAF = (82, 172, 42)
COLOR_STEM = (118, 84, 46)
COLOR_WHITE = (255, 255, 255)

COLOR_CARD_SKY = (76, 194, 248)
COLOR_CARD_GRASS_1 = (150, 214, 68)
COLOR_CARD_GRASS_2 = (134, 198, 56)
COLOR_BTN_BLUE = (17, 85, 204)
COLOR_BTN_HOVER = (28, 102, 228)


# ==========================================
# مسیر پوشه بازی، پوشه sound و پوشه data برای رکوردهای دائمی
# ==========================================
def get_base_dir():
    """مسیر اصلی پروژه (کنار فایل اجرایی یا اسکریپت)"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    if "__file__" in globals():
        return os.path.dirname(os.path.abspath(__file__))
    return os.getcwd()


def get_resource_dir():
    """مسیر منابع در حالت EXE (استخراج در پوشه موقت ویندوز)"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return get_base_dir()


PROJECT_DIR = get_base_dir()
RESOURCE_DIR = get_resource_dir()

# ۱. تنظیم مسیر پوشه صداها (sound)
SOUND_DIR = os.path.join(RESOURCE_DIR, "sound")
if not os.path.isdir(SOUND_DIR):
    SOUND_DIR = os.path.join(PROJECT_DIR, "sound")

# ۲. ساخت خودکار پوشه data و ذخیره رکورد داخل data/highscore.json
DATA_DIR = os.path.join(PROJECT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
HIGHSCORE_FILE = os.path.join(DATA_DIR, "highscore.json")


def load_high_score():
    if os.path.isfile(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
                return int(json.load(f).get("high_score", 0))
        except Exception:
            pass
    return 0


def save_high_score(val):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            json.dump({"high_score": int(val)}, f)
    except Exception:
        pass


# ==========================================
# تنظیم پنجره و آیکون بازی (سازگار با پایتون و EXE)
# ==========================================
if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "amir.gamesnake.clone.1"
        )
    except Exception:
        pass

screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF
)
pygame.display.set_caption("Snake Game")

ICON_PATH_PNG = os.path.join(RESOURCE_DIR, "icon.png")
if not os.path.isfile(ICON_PATH_PNG):
    ICON_PATH_PNG = os.path.join(PROJECT_DIR, "icon.png")

if os.path.isfile(ICON_PATH_PNG):
    try:
        game_icon = pygame.image.load(ICON_PATH_PNG)
        pygame.display.set_icon(game_icon)
    except Exception:
        pass

clock = pygame.time.Clock()
font_top = pygame.font.SysFont("segoeui", 26, bold=True)
font_card_score = pygame.font.SysFont("segoeui", 38, bold=True)
font_btn = pygame.font.SysFont("segoeui", 21, bold=True)


# ==========================================
# بارگذاری مستقیم sound/eat_apple.wav
# ==========================================
EAT_APPLE_PATH = os.path.join(SOUND_DIR, "eat_apple.wav")
if not os.path.isfile(EAT_APPLE_PATH):
    EAT_APPLE_PATH = os.path.join(PROJECT_DIR, "eat_apple.wav")

try:
    sound_eat = pygame.mixer.Sound(EAT_APPLE_PATH)
    sound_eat.set_volume(1.0)
except Exception:
    sound_eat = None


def play_eat_sound(muted):
    if muted:
        return
    if sound_eat is not None:
        sound_eat.play()


# ==========================================
# بارگذاری صداهای حرکت (از پوشه sound یا پوشه اصلی)
# ==========================================
def _to_wav_sound(samples):
    buf = io.BytesIO()
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        packed = struct.pack(f"<{len(samples)}h", *samples)
        wf.writeframesraw(packed)
    buf.seek(0)
    return pygame.mixer.Sound(buf)


def generate_move_pop_samples(f_start, f_end, dur=0.065):
    sr = 44100
    n = int(sr * dur)
    samples = []
    phase = 0.0
    for i in range(n):
        t = i / sr
        p = t / dur
        freq = f_start + (f_end - f_start) * (p ** 0.65)
        phase += freq / sr
        attack = min(1.0, t / 0.004)
        decay = math.exp(-p * 4.5) * math.sin((1.0 - p * 0.3) * (math.pi / 2.0))
        env = attack * decay
        sin_w = math.sin(2.0 * math.pi * phase)
        tri_w = 2.0 * abs(2.0 * (phase - math.floor(phase + 0.5))) - 1.0
        sub_w = math.sin(4.0 * math.pi * phase)
        val = (0.76 * sin_w + 0.16 * tri_w + 0.08 * sub_w) * env
        samples.append(max(-32767, min(32767, int(val * 0.72 * 32767))))
    return samples


class RandomTurnSoundManager:
    def __init__(self):
        self.sounds = []
        self.last_idx = -1
        presets = [
            ("move_1.wav", 168.0, 125.0, 0.068),
            ("move_2.wav", 198.0, 152.0, 0.064),
            ("move_3.wav", 228.0, 185.0, 0.062),
            ("move_4.wav", 262.0, 215.0, 0.060),
        ]
        for filename, f1, f2, dur in presets:
            wav_in_sound = os.path.join(SOUND_DIR, filename)
            wav_in_root = os.path.join(PROJECT_DIR, filename)
            wav_path = (
                wav_in_sound if os.path.isfile(wav_in_sound) else wav_in_root
            )

            if os.path.isfile(wav_path):
                try:
                    s = pygame.mixer.Sound(wav_path)
                    s.set_volume(0.85)
                    self.sounds.append(s)
                    continue
                except Exception:
                    pass
            self.sounds.append(
                _to_wav_sound(generate_move_pop_samples(f1, f2, dur))
            )

    def play_random(self, muted=False):
        if muted or not self.sounds:
            return
        if len(self.sounds) == 1:
            self.sounds[0].play()
            return
        available = [i for i in range(len(self.sounds)) if i != self.last_idx]
        chosen = random.choice(available)
        self.last_idx = chosen
        self.sounds[chosen].play()


def make_die_sound():
    sr = 44100
    dur = 0.52
    n = int(sr * dur)
    samples = []
    phase = 0.0
    rng = random.Random(99)
    for i in range(n):
        t = i / sr
        if t < 0.09:
            p = t / 0.09
            freq = 155.0 - p * 75.0
            phase += freq / sr
            env = math.exp(-p * 2.8)
            impact_noise = (rng.random() * 2.0 - 1.0) * 0.25 * math.exp(-p * 5.0)
            val = (math.sin(2.0 * math.pi * phase) + impact_noise) * env * 0.85
        else:
            t2 = t - 0.09
            dur2 = dur - 0.09
            p2 = t2 / dur2
            wobble = math.sin(2.0 * math.pi * 19.0 * t2) * 14.0
            freq = 132.0 - p2 * 48.0 + wobble
            phase += freq / sr
            env = math.exp(-p2 * 3.2)
            saw = 2.0 * (phase - math.floor(phase + 0.5))
            sin_w = math.sin(2.0 * math.pi * phase)
            sq = 1.0 if sin_w >= 0 else -1.0
            val = (0.50 * sin_w + 0.35 * saw + 0.15 * sq) * env * 0.75
        samples.append(max(-32767, min(32767, int(val * 32767))))
    return _to_wav_sound(samples)


def make_click_sound():
    sr = 44100
    dur = 0.055
    n = int(sr * dur)
    samples = []
    phase = 0.0
    for i in range(n):
        t = i / sr
        p = t / dur
        freq = 380.0 + p * 260.0
        phase += freq / sr
        env = math.exp(-p * 5.0)
        val = math.sin(2.0 * math.pi * phase) * env * 0.5
        samples.append(int(val * 32767))
    return _to_wav_sound(samples)


sound_die = make_die_sound()
sound_click = make_click_sound()
turn_sound_manager = RandomTurnSoundManager()


def set_global_mute(muted):
    if muted:
        pygame.mixer.stop()


# ==========================================
# توابع گرافیکی (سیب، جام، بلندگو و مار)
# ==========================================
def draw_rotated_ellipse(surface, color, center, rx, ry, angle_deg):
    if rx < 1 or ry < 1:
        return
    pts = []
    rad = math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    steps = 16
    for i in range(steps):
        t = (2.0 * math.pi * i) / steps
        ex = rx * math.cos(t)
        ey = ry * math.sin(t)
        px = center[0] + ex * ca - ey * sa
        py = center[1] + ex * sa + ey * ca
        pts.append((int(px), int(py)))
    pygame.draw.polygon(surface, color, pts)


def draw_apple_at_center(surface, cx, cy, scale=1.0, has_shadow=True):
    if scale <= 0.05:
        return
    radius = max(2, int((GRID_SIZE // 2 - 2) * scale))
    cx, cy = int(cx), int(cy + 1)

    if has_shadow:
        pygame.draw.ellipse(
            surface,
            COLOR_SHADOW,
            (cx - radius, int(cy + radius * 0.35), radius * 2, int(radius * 0.85)),
        )

    apple_rect = pygame.Rect(
        cx - radius,
        cy - int(radius * 0.92),
        radius * 2,
        int(radius * 1.9),
    )
    pygame.draw.ellipse(surface, COLOR_APPLE, apple_rect)

    if radius >= 5:
        hl_cx = cx - int(radius * 0.38)
        hl_cy = cy - int(radius * 0.32)
        draw_rotated_ellipse(
            surface,
            COLOR_APPLE_HIGHLIGHT,
            (hl_cx, hl_cy),
            max(2.0, radius * 0.34),
            max(1.2, radius * 0.19),
            -38,
        )

        stem_top_y = int(cy - radius * 0.92 - 5 * scale)
        stem_bot_y = int(cy - radius * 0.78)
        pygame.draw.line(
            surface,
            COLOR_STEM,
            (cx - 1, stem_bot_y),
            (cx - 1, stem_top_y),
            max(2, int(2.6 * scale)),
        )

        leaf_cx = cx + int(5.5 * scale)
        leaf_cy = stem_top_y + int(1.5 * scale)
        draw_rotated_ellipse(
            surface,
            COLOR_LEAF,
            (leaf_cx, leaf_cy),
            max(3.0, 6.2 * scale),
            max(1.8, 3.0 * scale),
            -18,
        )


def draw_trophy(surface, cx, cy, scale=1.0):
    GOLD = (252, 194, 12)
    GOLD_LIGHT = (255, 220, 55)
    GOLD_DARK = (228, 158, 0)
    s = scale
    handle_rect_l = pygame.Rect(
        int(cx - 18 * s), int(cy - 14 * s), int(12 * s), int(16 * s)
    )
    handle_rect_r = pygame.Rect(
        int(cx + 6 * s), int(cy - 14 * s), int(12 * s), int(16 * s)
    )
    pygame.draw.rect(
        surface,
        GOLD_DARK,
        handle_rect_l,
        width=max(2, int(3 * s)),
        border_radius=int(4 * s),
    )
    pygame.draw.rect(
        surface,
        GOLD_DARK,
        handle_rect_r,
        width=max(2, int(3 * s)),
        border_radius=int(4 * s),
    )
    cup_pts = [
        (cx - 12 * s, cy - 16 * s),
        (cx + 12 * s, cy - 16 * s),
        (cx + 9 * s, cy + 2 * s),
        (cx - 9 * s, cy + 2 * s),
    ]
    pygame.draw.polygon(surface, GOLD, cup_pts)
    pygame.draw.circle(surface, GOLD, (int(cx), int(cy - 2 * s)), int(9 * s))
    hl_pts = [
        (cx - 11 * s, cy - 15 * s),
        (cx - 2 * s, cy - 15 * s),
        (cx - 2 * s, cy + 4 * s),
        (cx - 8 * s, cy + 1 * s),
    ]
    pygame.draw.polygon(surface, GOLD_LIGHT, hl_pts)
    pygame.draw.rect(
        surface,
        GOLD_DARK,
        (int(cx - 2.5 * s), int(cy + 5 * s), int(5 * s), int(9 * s)),
    )
    pygame.draw.rect(
        surface,
        GOLD,
        (int(cx - 9 * s), int(cy + 13 * s), int(18 * s), int(4 * s)),
        border_radius=int(2 * s),
    )


def draw_speaker_icon(surface, x, y, muted, hovered=False):
    if hovered:
        pygame.draw.circle(surface, (92, 142, 56), (x, y), 20)

    pygame.draw.polygon(
        surface,
        COLOR_WHITE,
        [
            (x - 9, y - 5),
            (x - 3, y - 5),
            (x + 4, y - 11),
            (x + 4, y + 11),
            (x - 3, y + 5),
            (x - 9, y + 5),
        ],
    )
    if muted:
        pygame.draw.line(
            surface, COLOR_WHITE, (x + 8, y - 5), (x + 16, y + 5), 3
        )
        pygame.draw.line(
            surface, COLOR_WHITE, (x + 8, y + 5), (x + 16, y - 5), 3
        )
    else:
        pygame.draw.arc(
            surface, COLOR_WHITE, (x + 1, y - 7, 10, 14), -0.85, 0.85, 2
        )
        pygame.draw.arc(
            surface, COLOR_WHITE, (x + 3, y - 11, 15, 22), -0.85, 0.85, 2
        )


def draw_gear_icon(surface, cx, cy, radius=11):
    for i in range(8):
        ang = i * (math.pi / 4)
        x1 = cx + math.cos(ang) * (radius - 3)
        y1 = cy + math.sin(ang) * (radius - 3)
        x2 = cx + math.cos(ang) * (radius + 3)
        y2 = cy + math.sin(ang) * (radius + 3)
        pygame.draw.line(
            surface, COLOR_WHITE, (int(x1), int(y1)), (int(x2), int(y2)), 4
        )
    pygame.draw.circle(surface, COLOR_WHITE, (cx, cy), radius - 1)
    pygame.draw.circle(surface, COLOR_BTN_BLUE, (cx, cy), radius - 6)


def get_semicircle_points(cx, cy, dx, dy, px, py, radius, steps=20):
    pts = []
    for i in range(steps + 1):
        ang = -math.pi / 2 + (math.pi * i / steps)
        ca, sa = math.cos(ang), math.sin(ang)
        x = cx + (dx * ca + px * sa) * radius
        y = cy + (dy * ca + py * sa) * radius
        pts.append((x, y))
    return pts


def get_smooth_snake_points(
    snake, prev_tail, move_progress, just_grew, board_x, board_y
):
    def to_px(cell):
        return (
            board_x + cell[0] * GRID_SIZE + GRID_SIZE / 2.0,
            board_y + cell[1] * GRID_SIZE + GRID_SIZE / 2.0,
        )

    if len(snake) < 2:
        return [to_px(snake[0])]

    p0 = to_px(snake[0])
    p1 = to_px(snake[1])
    head_px = (
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
        tail_px = (
            pt_px[0] + (last_seg[0] - pt_px[0]) * move_progress,
            pt_px[1] + (last_seg[1] - pt_px[1]) * move_progress,
        )
        pts.append(tail_px)
        pts.insert(-1, last_seg)

    return pts


def build_curved_spine(pts, corner_radius=15.0, arc_steps=12):
    if len(pts) < 3:
        return list(pts)
    curved = [pts[0]]
    for i in range(1, len(pts) - 1):
        p_prev = pts[i - 1]
        p_curr = pts[i]
        p_next = pts[i + 1]
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
        start_pt = (p_curr[0] - ux1 * r, p_curr[1] - uy1 * r)
        end_pt = (p_curr[0] + ux2 * r, p_curr[1] + uy2 * r)
        for s in range(arc_steps + 1):
            t = s / arc_steps
            mt = 1.0 - t
            bx = mt * mt * start_pt[0] + 2 * mt * t * p_curr[0] + t * t * end_pt[0]
            by = mt * mt * start_pt[1] + 2 * mt * t * p_curr[1] + t * t * end_pt[1]
            curved.append((bx, by))
    curved.append(pts[-1])
    return curved


def draw_smooth_snake(
    surface,
    pts,
    bulges,
    head_dir_vec,
    apple_px,
    mouth_anim,
    eating_apple,
    is_dizzy=False,
    dizzy_timer=0.0,
    recoil_px=0.0,
):
    snake_radius = 13
    spine = build_curved_spine(pts, corner_radius=15.5, arc_steps=12)

    uniform_pts = [spine[0]]
    total_len = 0.0
    cum_lengths = [0.0]
    for i in range(len(spine) - 1):
        x1, y1 = spine[i]
        x2, y2 = spine[i + 1]
        seg_d = math.hypot(x2 - x1, y2 - y1)
        if seg_d < 0.001:
            continue
        steps = max(1, int(seg_d / 1.5))
        for s in range(1, steps + 1):
            t = s / steps
            px_i = x1 + (x2 - x1) * t
            py_i = y1 + (y2 - y1) * t
            step_d = math.hypot(
                px_i - uniform_pts[-1][0], py_i - uniform_pts[-1][1]
            )
            total_len += step_d
            uniform_pts.append((px_i, py_i))
            cum_lengths.append(total_len)

    dx, dy = head_dir_vec
    num_u = len(uniform_pts)

    if not is_dizzy and num_u > 5:
        tx_dir = uniform_pts[0][0] - uniform_pts[5][0]
        ty_dir = uniform_pts[0][1] - uniform_pts[5][1]
        td_len = math.hypot(tx_dir, ty_dir)
        if td_len > 0.001:
            bx = dx * 0.60 + (tx_dir / td_len) * 0.40
            by = dy * 0.60 + (ty_dir / td_len) * 0.40
            b_len = math.hypot(bx, by)
            if b_len > 0.001:
                dx, dy = bx / b_len, by / b_len

    if recoil_px > 0.0:
        recoil_span = 65.0
        for i in range(num_u):
            if cum_lengths[i] < recoil_span:
                factor = math.cos((cum_lengths[i] / recoil_span) * (math.pi / 2.0))
                uniform_pts[i] = (
                    uniform_pts[i][0] - dx * recoil_px * factor,
                    uniform_pts[i][1] - dy * recoil_px * factor,
                )
            else:
                break

    hx, hy = uniform_pts[0]
    px, py = -dy, dx

    def body_color(ratio):
        r = int(COLOR_SNAKE_HEAD[0] * (1 - ratio) + COLOR_SNAKE_TAIL[0] * ratio)
        g = int(COLOR_SNAKE_HEAD[1] * (1 - ratio) + COLOR_SNAKE_TAIL[1] * ratio)
        b = int(COLOR_SNAKE_HEAD[2] * (1 - ratio) + COLOR_SNAKE_TAIL[2] * ratio)
        return (r, g, b)

    def radius_at(dist_val, ratio):
        r_base = float(snake_radius)
        if ratio > 0.88:
            t_tail = (ratio - 0.88) / 0.12
            r_base = max(9.5, snake_radius * (1.0 - 0.18 * (t_tail ** 1.5)))
        extra_bulge = 0.0
        for b_dist in bulges:
            diff = abs(dist_val - b_dist)
            if diff < 15.0:
                extra_bulge = max(
                    extra_bulge, 6.0 * math.cos((diff / 15.0) * (math.pi / 2.0))
                )
        return int(round(r_base + extra_bulge))

    for i in range(num_u - 1, -1, -1):
        ratio = cum_lengths[i] / max(1.0, total_len)
        rad = radius_at(cum_lengths[i], ratio)
        pygame.draw.circle(
            surface,
            COLOR_SHADOW,
            (int(uniform_pts[i][0]), int(uniform_pts[i][1] + 4)),
            rad,
        )

    pygame.draw.circle(
        surface,
        COLOR_SHADOW,
        (int(hx + dx * 4.0), int(hy + dy * 4.0 + 4)),
        snake_radius,
    )

    for side in [-1, 1]:
        ex = hx - dx * 1.5 + px * 10.0 * side
        ey = hy - dy * 1.5 + py * 10.0 * side + 4
        pygame.draw.circle(surface, COLOR_SHADOW, (int(ex), int(ey)), 9)

    if mouth_anim > 0.05 and not is_dizzy:
        lip_cx = hx + dx * 6
        lip_cy = hy + dy * 6 + 4
        outer_r = snake_radius + 5 * mouth_anim
        shadow_jaw = get_semicircle_points(
            lip_cx, lip_cy, dx, dy, px, py, outer_r
        )
        pygame.draw.polygon(surface, COLOR_SHADOW, shadow_jaw)

    for i in range(num_u - 1, -1, -1):
        ratio = cum_lengths[i] / max(1.0, total_len)
        rad = radius_at(cum_lengths[i], ratio)
        pygame.draw.circle(
            surface,
            body_color(ratio),
            (int(uniform_pts[i][0]), int(uniform_pts[i][1])),
            rad,
        )

    if mouth_anim < 0.12 and not is_dizzy:
        t_wave = (math.sin(pygame.time.get_ticks() * 0.012) + 1) * 0.5
        if t_wave > 0.35:
            t_len = 6 + int(t_wave * 6)
            bx = hx + dx * (snake_radius + 3.5)
            by = hy + dy * (snake_radius + 3.5)
            tx = bx + dx * t_len
            ty = by + dy * t_len
            pygame.draw.line(surface, COLOR_TONGUE, (bx, by), (tx, ty), 3)
            pygame.draw.line(
                surface,
                COLOR_TONGUE,
                (tx, ty),
                (tx + dx * 4 + px * 3, ty + dy * 4 + py * 3),
                2,
            )
            pygame.draw.line(
                surface,
                COLOR_TONGUE,
                (tx, ty),
                (tx + dx * 4 - px * 3, ty + dy * 4 - py * 3),
                2,
            )

    pygame.draw.circle(
        surface,
        COLOR_SNAKE_HEAD,
        (int(hx + dx * 2.2), int(hy + dy * 2.2)),
        snake_radius,
    )
    pygame.draw.circle(
        surface,
        COLOR_SNAKE_HEAD,
        (int(hx + dx * 4.8), int(hy + dy * 4.8)),
        snake_radius - 1,
    )

    if mouth_anim > 0.04 and not is_dizzy:
        lip_cx = hx + dx * 6
        lip_cy = hy + dy * 6
        outer_r = snake_radius + 5.5 * mouth_anim
        outer_jaw_pts = get_semicircle_points(
            lip_cx, lip_cy, dx, dy, px, py, outer_r
        )
        pygame.draw.polygon(surface, COLOR_SNAKE_HEAD, outer_jaw_pts)

        inner_cx = hx + dx * 7.5
        inner_cy = hy + dy * 7.5
        inner_r = (snake_radius - 2) * mouth_anim + 2.5 * mouth_anim
        if inner_r > 2:
            inner_jaw_pts = get_semicircle_points(
                inner_cx, inner_cy, dx, dy, px, py, inner_r
            )
            pygame.draw.polygon(surface, COLOR_MOUTH_INSIDE, inner_jaw_pts)

        if eating_apple is not None:
            draw_apple_at_center(
                surface,
                eating_apple["x"],
                eating_apple["y"],
                scale=eating_apple["scale"],
                has_shadow=False,
            )

        if mouth_anim > 0.25:
            fang_len = 5.0 * mouth_anim
            for side in [-1, 1]:
                fx = inner_cx + px * 5.5 * side
                fy = inner_cy + py * 5.5 * side
                fang_pts = [
                    (fx - px * 2.2 * side, fy - py * 2.2 * side),
                    (fx + px * 2.2 * side, fy + py * 2.2 * side),
                    (fx + dx * fang_len, fy + dy * fang_len),
                ]
                pygame.draw.polygon(surface, COLOR_WHITE, fang_pts)

    look_x, look_y = dx, dy
    dist_to_apple = math.hypot(apple_px[0] - hx, apple_px[1] - hy)
    if dist_to_apple > 1:
        look_x = (apple_px[0] - hx) / dist_to_apple
        look_y = (apple_px[1] - hy) / dist_to_apple

    for idx, side in enumerate([-1, 1]):
        ex = hx - dx * 1.5 + px * 10.0 * side
        ey = hy - dy * 1.5 + py * 10.0 * side
        pygame.draw.circle(surface, COLOR_SNAKE_OUTLINE, (int(ex), int(ey)), 9)
        pygame.draw.circle(surface, COLOR_SNAKE_HEAD, (int(ex), int(ey)), 8)

        eye_white_r = 6
        pygame.draw.circle(
            surface, COLOR_WHITE, (int(ex), int(ey)), eye_white_r
        )

        if is_dizzy:
            ang = dizzy_timer * 14.0 * side + (idx * 2.4)
            px_off = ex + math.cos(ang) * 2.5
            py_off = ey + math.sin(ang) * 2.5
            pupil_r = 3.5 if idx == 0 else 2.8
            pygame.draw.circle(
                surface, COLOR_PUPIL, (int(px_off), int(py_off)), int(pupil_r)
            )
        else:
            px_off = ex + look_x * 2.3
            py_off = ey + look_y * 2.3
            pygame.draw.circle(
                surface, COLOR_PUPIL, (int(px_off), int(py_off)), 3
            )

        nx = hx + dx * 5.8 + px * 3.6 * side
        ny = hy + dy * 5.8 + py * 3.6 * side
        pygame.draw.circle(surface, COLOR_PUPIL, (int(nx), int(ny)), 1.6)


def draw_menu_card_modal(
    surface, score, high_score, button_label="Play Snake", mouse_pos=(0, 0)
):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((12, 22, 8, 135))
    surface.blit(overlay, (0, 0))

    card_w, card_h = 300, 315
    cx = (SCREEN_WIDTH - card_w) // 2
    cy = (SCREEN_HEIGHT - card_h) // 2 - 14

    shadow_rect = pygame.Rect(cx - 4, cy - 2, card_w + 8, card_h + 8)
    shadow_surf = pygame.Surface(
        (shadow_rect.width, shadow_rect.height), pygame.SRCALPHA
    )
    pygame.draw.rect(
        shadow_surf,
        (0, 0, 0, 55),
        (0, 0, shadow_rect.width, shadow_rect.height),
        border_radius=14,
    )
    surface.blit(shadow_surf, shadow_rect.topleft)

    card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
    pygame.draw.rect(
        card_surf, COLOR_CARD_SKY, (0, 0, card_w, card_h), border_radius=12
    )

    grass_rows = 3
    cell_s = 30
    grass_top_y = card_h - grass_rows * cell_s
    for r in range(grass_rows):
        for c in range(card_w // cell_s):
            col = (
                COLOR_CARD_GRASS_1
                if (r + c) % 2 == 0
                else COLOR_CARD_GRASS_2
            )
            rect = pygame.Rect(
                c * cell_s, grass_top_y + r * cell_s, cell_s, cell_s
            )
            pygame.draw.rect(card_surf, col, rect)

    mask_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
    pygame.draw.rect(
        mask_surf,
        (255, 255, 255, 255),
        (0, 0, card_w, card_h),
        border_radius=12,
    )

    snake_y = grass_top_y - 32
    body_h = 32
    pygame.draw.rect(
        card_surf, COLOR_SNAKE_HEAD, (-15, snake_y, 190, body_h)
    )
    pygame.draw.circle(
        card_surf,
        COLOR_SNAKE_HEAD,
        (175, snake_y + body_h // 2),
        body_h // 2,
    )
    pygame.draw.ellipse(
        card_surf, COLOR_SNAKE_HEAD, (122, snake_y - 6, 65, 24)
    )

    eye1_x, eye2_x = 122, 142
    eye_y = snake_y - 5
    pygame.draw.circle(card_surf, COLOR_SNAKE_HEAD, (eye1_x, eye_y), 11)
    pygame.draw.circle(card_surf, COLOR_SNAKE_HEAD, (eye2_x, eye_y), 11)

    for ex in [eye1_x, eye2_x]:
        pygame.draw.circle(card_surf, COLOR_WHITE, (ex, eye_y), 7.5)
        pygame.draw.circle(card_surf, COLOR_PUPIL, (ex - 2, eye_y - 1), 4)

    pygame.draw.ellipse(
        card_surf, COLOR_PUPIL, (176, snake_y + 2, 2.5, 5.5)
    )
    pygame.draw.ellipse(
        card_surf, COLOR_PUPIL, (183, snake_y + 2, 2.5, 5.5)
    )

    mouth_y = snake_y + 17
    pygame.draw.line(
        card_surf, COLOR_PUPIL, (120, mouth_y), (189, mouth_y), 2
    )
    pygame.draw.arc(
        card_surf,
        COLOR_PUPIL,
        (112, mouth_y - 6, 14, 10),
        math.pi,
        1.85 * math.pi,
        2,
    )

    draw_apple_at_center(card_surf, 88, 78, scale=1.8, has_shadow=False)
    s_txt = font_card_score.render(str(score), True, COLOR_WHITE)
    card_surf.blit(s_txt, s_txt.get_rect(center=(88, 142)))

    draw_trophy(card_surf, 212, 78, scale=1.65)
    h_txt = font_card_score.render(str(high_score), True, COLOR_WHITE)
    card_surf.blit(h_txt, h_txt.get_rect(center=(212, 142)))

    card_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(card_surf, (cx, cy))

    btn_y = cy + card_h + 14
    play_btn_rect = pygame.Rect(cx, btn_y, 224, 52)
    gear_btn_rect = pygame.Rect(cx + 236, btn_y, 64, 52)

    is_play_hover = play_btn_rect.collidepoint(mouse_pos)
    is_gear_hover = gear_btn_rect.collidepoint(mouse_pos)

    pygame.draw.rect(
        surface,
        COLOR_BTN_HOVER if is_play_hover else COLOR_BTN_BLUE,
        play_btn_rect,
        border_radius=10,
    )
    pygame.draw.rect(
        surface,
        COLOR_BTN_HOVER if is_gear_hover else COLOR_BTN_BLUE,
        gear_btn_rect,
        border_radius=10,
    )

    b_txt = font_btn.render(button_label, True, COLOR_WHITE)
    total_w = 24 + b_txt.get_width()
    start_x = play_btn_rect.centerx - total_w // 2

    tri_cx = start_x + 6
    tri_cy = play_btn_rect.centery
    tri_pts = [
        (tri_cx - 6, tri_cy - 8),
        (tri_cx - 6, tri_cy + 8),
        (tri_cx + 7, tri_cy),
    ]
    pygame.draw.polygon(surface, COLOR_WHITE, tri_pts, width=2)

    surface.blit(
        b_txt, b_txt.get_rect(midleft=(tri_cx + 16, play_btn_rect.centery))
    )

    draw_gear_icon(surface, gear_btn_rect.centerx, gear_btn_rect.centery, 12)
    return play_btn_rect


def main():
    board_x = BORDER_SIZE
    board_y = TOP_BAR_HEIGHT + BORDER_SIZE

    def cell_center(cell):
        return (
            board_x + cell[0] * GRID_SIZE + GRID_SIZE / 2.0,
            board_y + cell[1] * GRID_SIZE + GRID_SIZE / 2.0,
        )

    def reset_state():
        snake = [(4, 7), (3, 7), (2, 7)]
        direction = (1, 0)
        apple = (11, 7)
        return snake, direction, apple

    snake, direction, apple = reset_state()
    prev_tail = snake[-1]
    just_grew = False
    input_queue = []
    bulges = []
    particles = []
    eating_apple = None
    apple_spawn_scale = 1.0

    smooth_head_dir = [float(direction[0]), float(direction[1])]

    score = 0
    high_score = load_high_score()
    # ساخت اولیه فایل در پوشه data به محض اجرای بازی
    save_high_score(high_score)
    muted = False

    game_state = "WAITING"
    state_before_pause = "WAITING"
    dying_timer = 0.0
    DYING_DURATION = 0.85
    death_progress = 1.0

    MOVE_INTERVAL = 145.0
    move_timer = MOVE_INTERVAL
    mouth_anim = 0.0

    speaker_rect = pygame.Rect(SCREEN_WIDTH - 58, 8, 44, 44)
    active_modal_btn_rect = pygame.Rect(0, 0, 0, 0)

    while True:
        dt_ms = clock.tick(60)
        dt_sec = min(0.05, dt_ms / 1000.0)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_high_score(high_score)
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if speaker_rect.collidepoint((mx, my)):
                    muted = not muted
                    set_global_mute(muted)
                    if not muted:
                        sound_click.play()

                elif game_state == "PAUSED":
                    if active_modal_btn_rect.collidepoint((mx, my)):
                        if not muted:
                            sound_click.play()
                        game_state = state_before_pause

                elif game_state == "GAMEOVER":
                    if active_modal_btn_rect.collidepoint((mx, my)) or True:
                        if not muted:
                            sound_click.play()
                        snake, direction, apple = reset_state()
                        prev_tail = snake[-1]
                        just_grew = False
                        input_queue.clear()
                        bulges.clear()
                        particles.clear()
                        eating_apple = None
                        smooth_head_dir = [
                            float(direction[0]),
                            float(direction[1]),
                        ]
                        score = 0
                        move_timer = MOVE_INTERVAL
                        death_progress = 1.0
                        game_state = "WAITING"

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    muted = not muted
                    set_global_mute(muted)

                elif event.key == pygame.K_ESCAPE:
                    if game_state in ["PLAYING", "WAITING"]:
                        if not muted:
                            sound_click.play()
                        state_before_pause = game_state
                        game_state = "PAUSED"
                    elif game_state == "PAUSED":
                        if not muted:
                            sound_click.play()
                        game_state = state_before_pause

                elif game_state == "PAUSED" and event.key in [
                    pygame.K_SPACE,
                    pygame.K_RETURN,
                ]:
                    if not muted:
                        sound_click.play()
                    game_state = state_before_pause

                elif game_state == "GAMEOVER" and event.key in [
                    pygame.K_SPACE,
                    pygame.K_RETURN,
                ]:
                    if not muted:
                        sound_click.play()
                    snake, direction, apple = reset_state()
                    prev_tail = snake[-1]
                    just_grew = False
                    input_queue.clear()
                    bulges.clear()
                    particles.clear()
                    eating_apple = None
                    smooth_head_dir = [
                        float(direction[0]),
                        float(direction[1]),
                    ]
                    score = 0
                    move_timer = MOVE_INTERVAL
                    death_progress = 1.0
                    game_state = "WAITING"

                elif game_state in ["WAITING", "PLAYING"]:
                    key_map = {
                        pygame.K_UP: (0, -1),
                        pygame.K_w: (0, -1),
                        pygame.K_DOWN: (0, 1),
                        pygame.K_s: (0, 1),
                        pygame.K_LEFT: (-1, 0),
                        pygame.K_a: (-1, 0),
                        pygame.K_RIGHT: (1, 0),
                        pygame.K_d: (1, 0),
                    }
                    if event.key in key_map:
                        new_dir = key_map[event.key]
                        last_dir = input_queue[-1] if input_queue else direction

                        if game_state == "WAITING":
                            if new_dir != (-direction[0], -direction[1]):
                                direction = new_dir
                                turn_sound_manager.play_random(muted)
                                game_state = "PLAYING"
                                move_timer = MOVE_INTERVAL
                        else:
                            if (
                                new_dir != last_dir
                                and new_dir != (-last_dir[0], -last_dir[1])
                                and len(input_queue) < 2
                            ):
                                input_queue.append(new_dir)
                                turn_sound_manager.play_random(muted)

        if game_state == "PLAYING" and not input_queue:
            keys = pygame.key.get_pressed()
            held_dirs = []
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                held_dirs.append((0, -1))
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                held_dirs.append((0, 1))
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                held_dirs.append((-1, 0))
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                held_dirs.append((1, 0))

            if len(held_dirs) == 2 and direction in held_dirs:
                other_dir = (
                    held_dirs[1] if held_dirs[0] == direction else held_dirs[0]
                )
                if other_dir != (-direction[0], -direction[1]):
                    input_queue.append(other_dir)

        if game_state == "PLAYING":
            move_timer += dt_ms
            while move_timer >= MOVE_INTERVAL:
                move_timer -= MOVE_INTERVAL

                next_dir = input_queue.pop(0) if input_queue else direction
                head_x, head_y = snake[0]
                new_head = (head_x + next_dir[0], head_y + next_dir[1])

                if (
                    new_head[0] < 0
                    or new_head[0] >= GRID_WIDTH
                    or new_head[1] < 0
                    or new_head[1] >= GRID_HEIGHT
                    or new_head in snake[:-1]
                ):
                    direction = next_dir
                    smooth_head_dir = [float(direction[0]), float(direction[1])]
                    death_progress = 1.0
                    game_state = "DYING"
                    dying_timer = 0.0
                    mouth_anim = 0.0
                    eating_apple = None
                    save_high_score(high_score)
                    if not muted:
                        sound_die.play()
                    break
                else:
                    direction = next_dir
                    prev_tail = snake[-1]
                    snake.insert(0, new_head)

                    if new_head == apple:
                        just_grew = True
                        ax, ay = cell_center(apple)

                        score += 1
                        if score > high_score:
                            high_score = score
                            save_high_score(high_score)
                        play_eat_sound(muted)
                        bulges.append(6.0)

                        for _ in range(8):
                            ang = random.uniform(0, 2 * math.pi)
                            spd = random.uniform(55, 125)
                            particles.append(
                                {
                                    "x": ax,
                                    "y": ay,
                                    "vx": math.cos(ang) * spd,
                                    "vy": math.sin(ang) * spd,
                                    "r": random.uniform(2.5, 4.5),
                                    "life": 1.0,
                                }
                            )

                        eating_apple = {
                            "start_x": ax,
                            "start_y": ay,
                            "x": ax,
                            "y": ay,
                            "scale": 1.0,
                            "timer": 0.0,
                            "duration": MOVE_INTERVAL * 0.95,
                        }
                        while True:
                            apple = (
                                random.randint(0, GRID_WIDTH - 1),
                                random.randint(0, GRID_HEIGHT - 1),
                            )
                            if apple not in snake:
                                break
                        apple_spawn_scale = 0.0
                    else:
                        just_grew = False
                        snake.pop()

        elif game_state == "DYING":
            dying_timer += dt_sec
            if dying_timer >= DYING_DURATION:
                game_state = "GAMEOVER"

        if game_state == "PLAYING":
            smooth_head_dir[0] += (direction[0] - smooth_head_dir[0]) * min(
                1.0, dt_sec * 18.0
            )
            smooth_head_dir[1] += (direction[1] - smooth_head_dir[1]) * min(
                1.0, dt_sec * 18.0
            )
        sh_len = math.hypot(smooth_head_dir[0], smooth_head_dir[1])
        if sh_len > 0.001:
            norm_head_dir = (
                smooth_head_dir[0] / sh_len,
                smooth_head_dir[1] / sh_len,
            )
        else:
            norm_head_dir = (float(direction[0]), float(direction[1]))

        if game_state == "PLAYING":
            progress = min(1.0, move_timer / MOVE_INTERVAL)
        elif game_state == "PAUSED":
            progress = (
                1.0
                if state_before_pause == "WAITING"
                else min(1.0, move_timer / MOVE_INTERVAL)
            )
        elif game_state in ["DYING", "GAMEOVER"]:
            progress = death_progress
        else:
            progress = 1.0

        smooth_pts = get_smooth_snake_points(
            snake, prev_tail, progress, just_grew, board_x, board_y
        )

        recoil_px = 0.0
        if game_state in ["DYING", "GAMEOVER"]:
            recoil_p = min(1.0, dying_timer / 0.18)
            recoil_px = math.sin(recoil_p * (math.pi / 2.0)) * 12.0

        hx, hy = smooth_pts[0]

        if game_state != "PAUSED":
            if eating_apple is not None:
                eating_apple["timer"] += dt_ms
                p = min(1.0, eating_apple["timer"] / eating_apple["duration"])

                mouth_target_x = hx + norm_head_dir[0] * 8
                mouth_target_y = hy + norm_head_dir[1] * 8
                eating_apple["x"] = (
                    eating_apple["start_x"] * (1 - p) + mouth_target_x * p
                )
                eating_apple["y"] = (
                    eating_apple["start_y"] * (1 - p) + mouth_target_y * p
                )

                if p < 0.45:
                    eating_apple["scale"] = 1.0
                else:
                    eating_apple["scale"] = max(0.0, 1.0 - ((p - 0.45) / 0.55))

                if p >= 1.0:
                    eating_apple = None

            if apple_spawn_scale < 1.0:
                apple_spawn_scale = min(1.0, apple_spawn_scale + dt_sec * 5.0)

            if bulges and game_state == "PLAYING":
                max_body_px = (len(snake) - 1) * GRID_SIZE
                bulges = [b + 260.0 * dt_sec for b in bulges if b < max_body_px]

            for part in particles:
                part["x"] += part["vx"] * dt_sec
                part["y"] += part["vy"] * dt_sec
                part["life"] -= dt_sec * 3.0
            particles = [part for part in particles if part["life"] > 0]

            apple_center_px = cell_center(apple)
            dist_px = math.hypot(hx - apple_center_px[0], hy - apple_center_px[1])

            if game_state in ["DYING", "GAMEOVER"]:
                mouth_anim = 0.0
            elif eating_apple is not None:
                p = eating_apple["timer"] / eating_apple["duration"]
                target_mouth = 1.0 if p < 0.55 else 0.0
                mouth_anim += (target_mouth - mouth_anim) * min(1.0, dt_sec * 22.0)
            else:
                target_mouth = 1.0 if dist_px < GRID_SIZE * 2.5 else 0.0
                mouth_anim += (target_mouth - mouth_anim) * min(1.0, dt_sec * 14.0)
        else:
            apple_center_px = cell_center(apple)

        # رندر صفحه
        screen.fill(COLOR_BORDER)
        pygame.draw.rect(
            screen, COLOR_TOP_BAR, (0, 0, SCREEN_WIDTH, TOP_BAR_HEIGHT)
        )

        draw_apple_at_center(screen, 34, 30, scale=0.95, has_shadow=False)
        score_surf = font_top.render(str(score), True, COLOR_WHITE)
        screen.blit(score_surf, (58, 12))

        draw_trophy(screen, 130, 31, scale=0.85)
        high_surf = font_top.render(str(high_score), True, COLOR_WHITE)
        screen.blit(high_surf, (156, 12))

        for row in range(GRID_HEIGHT):
            for col in range(GRID_WIDTH):
                color = (
                    COLOR_LIGHT_GREEN
                    if (row + col) % 2 == 0
                    else COLOR_DARK_GREEN
                )
                pygame.draw.rect(
                    screen,
                    color,
                    (
                        board_x + col * GRID_SIZE,
                        board_y + row * GRID_SIZE,
                        GRID_SIZE,
                        GRID_SIZE,
                    ),
                )

        idle_pulse = 1.0 + math.sin(pygame.time.get_ticks() * 0.006) * 0.035
        draw_apple_at_center(
            screen,
            apple_center_px[0],
            apple_center_px[1],
            scale=apple_spawn_scale * idle_pulse,
            has_shadow=True,
        )

        target_look = (
            (eating_apple["x"], eating_apple["y"])
            if eating_apple is not None
            else apple_center_px
        )
        is_dizzy = game_state in ["DYING", "GAMEOVER"]
        draw_smooth_snake(
            screen,
            smooth_pts,
            bulges,
            norm_head_dir,
            target_look,
            mouth_anim,
            eating_apple,
            is_dizzy=is_dizzy,
            dizzy_timer=dying_timer,
            recoil_px=recoil_px,
        )

        for part in particles:
            pygame.draw.circle(
                screen,
                COLOR_APPLE,
                (int(part["x"]), int(part["y"])),
                max(1, int(part["r"] * part["life"])),
            )

        if game_state == "PAUSED":
            active_modal_btn_rect = draw_menu_card_modal(
                screen,
                score,
                high_score,
                button_label="Continue",
                mouse_pos=mouse_pos,
            )
        elif game_state == "GAMEOVER":
            active_modal_btn_rect = draw_menu_card_modal(
                screen,
                score,
                high_score,
                button_label="Play Snake",
                mouse_pos=mouse_pos,
            )

        draw_speaker_icon(
            screen,
            speaker_rect.centerx,
            speaker_rect.centery,
            muted,
            hovered=speaker_rect.collidepoint(mouse_pos),
        )

        pygame.display.flip()


if __name__ == "__main__":
    main()