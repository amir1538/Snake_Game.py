"""Snaky Game — Deterministic Core Game Engine (Zero Pygame Dependencies).

- Immediate keydown steering (first keydown steps immediately, 3-turn buffer, 180-deg guard).
- Pause-aware clocks (`game_time_ms`, `elapsed_ms`): pressing ESC freezes 100% of state,
  timers, tongue flick, apple pulse, swallowing bulges, eating animation, and mines.
"""

import math
import random
from typing import Callable, Dict, List, Optional, Set, Tuple

from . import constants as C
from .modes import ModeEngine


class GameEngine:
    """Core game simulation matching approved js/engine.js 1:1."""

    def __init__(
        self,
        settings_manager,
        audio_manager,
        rng: Optional[Callable[[], float]] = None,
    ) -> None:
        self.settings_manager = settings_manager
        self.audio = audio_manager
        self.rand = rng or random.random

        self.state = "MENU"  # MENU | WAITING | PLAYING | PAUSED | DYING | GAMEOVER | WON
        self.state_before_pause = "WAITING"
        self.death_reason: Optional[str] = None
        self.next_entity_id = 0
        self.cell_size = 32

        self.held_dirs: Set[str] = set()  # {"UP", "DOWN", "LEFT", "RIGHT"}
        self._moved_since_keydown = False

        # Mode entity lists initialized in reset()
        self.walls: List[Dict] = []
        self.statues: List[Dict] = []
        self.mines: List[Dict] = []
        self.keys: List[Dict] = []
        self.locks: List[Dict] = []
        self.crates: List[Dict] = []
        self.targets: List[Dict] = []
        self.poisons: List[Dict] = []
        self.active_dimension = 0
        self.poison_steps_remaining = 0
        self.light_radius = 3.5
        self.light_pulses: List[Dict] = []
        self.wing_tick_counter = 0
        self.yin_yang_snake: Optional[List[Dict]] = None
        self.yin_yang_prev_tail: Optional[Dict] = None
        self.yin_yang_dir = {"x": -1, "y": 0}
        self.yin_yang_just_grew = False

        self.reset(show_menu=True)

    def set_cell_size(self, px: int) -> None:
        clamped = max(12, int(px))
        if clamped != self.cell_size and self.cell_size > 0:
            ratio = clamped / self.cell_size
            self.bulges = [b * ratio for b in self.bulges]
            if self.eating_apple is not None:
                self.eating_apple["start_x"] *= ratio
                self.eating_apple["start_y"] *= ratio
                self.eating_apple["x"] *= ratio
                self.eating_apple["y"] *= ratio
            for p in self.particles:
                p["x"] *= ratio
                p["y"] *= ratio
            for lp in self.light_pulses:
                lp["dist"] *= ratio
            self.cell_size = clamped

    def reset(self, show_menu: bool = False) -> None:
        self.settings = self.settings_manager.get()
        self.active_modes = self.settings_manager.get_active_modes()

        board_cfg = C.BOARD_SIZES.get(self.settings["board_size"], C.BOARD_SIZES["regular"])
        speed_cfg = C.SPEEDS.get(self.settings["speed"], C.SPEEDS["snake"])

        self.cols = board_cfg["cols"]
        self.rows = board_cfg["rows"]
        self.move_interval_ms = float(speed_cfg["interval_ms"])

        mid_y = self.rows // 2
        head_x = max(3, min(4, int(self.cols * 0.25)))

        self.snake = [
            {"x": head_x, "y": mid_y},
            {"x": head_x - 1, "y": mid_y},
            {"x": head_x - 2, "y": mid_y},
        ]
        self.prev_tail = {"x": head_x - 2, "y": mid_y}
        self.just_grew = False
        self.direction = {"x": 1, "y": 0}
        self.smooth_head_dir = [1.0, 0.0]
        self.input_queue: List[Dict[str, int]] = []
        self._moved_since_keydown = False

        self.foods: List[Dict] = []
        self.score = 0
        self.high_score = self.settings_manager.get_high_score()

        # Pause-aware clocks: NEVER advance while PAUSED
        self.game_time_ms = 0.0
        self.elapsed_ms = 0.0
        self.move_timer_ms = self.move_interval_ms
        self.dying_timer_ms = 0.0
        self.dying_duration_ms = 850.0
        self.death_progress = 1.0

        self.mouth_anim = 0.0
        self.bulges: List[float] = []
        self.particles: List[Dict] = []
        self.eating_apple: Optional[Dict] = None
        self.recoil_px = 0.0
        self.step_count = 0

        self.state = "MENU" if show_menu else "WAITING"
        self.state_before_pause = self.state
        self.death_reason = None

        ModeEngine.init_mode_state(self)
        ModeEngine.ensure_foods(self, True)

    def start_from_menu(self) -> None:
        if self.state == "MENU":
            self.state = "WAITING"
            self.state_before_pause = "WAITING"

    def apply_settings_and_reset(self, keep_in_menu: bool = False) -> None:
        self.reset(show_menu=bool(keep_in_menu))

    def cell_center_px(self, cell: Dict[str, int]) -> Tuple[float, float]:
        return (
            cell["x"] * self.cell_size + self.cell_size / 2.0,
            cell["y"] * self.cell_size + self.cell_size / 2.0,
        )

    def queue_direction(self, dx: int, dy: int) -> bool:
        if self.state == "MENU":
            self.state = "WAITING"
        if self.state not in ("WAITING", "PLAYING"):
            return False

        new_dir = {"x": dx, "y": dy}
        last_dir = self.input_queue[-1] if self.input_queue else self.direction

        if new_dir["x"] == -last_dir["x"] and new_dir["y"] == -last_dir["y"]:
            return False

        self._moved_since_keydown = False

        if self.state == "WAITING":
            self.direction = new_dir
            self.smooth_head_dir = [float(dx), float(dy)]
            self.audio.play_turn(dx, dy)
            self.state = "PLAYING"
            self.move_timer_ms = 0.0
            self.step_once()
            return True

        if (new_dir["x"] != last_dir["x"] or new_dir["y"] != last_dir["y"]) and len(self.input_queue) < 3:
            self.input_queue.append(new_dir)
            self.audio.play_turn(dx, dy)
            if len(self.input_queue) == 1 and self.move_timer_ms >= self.move_interval_ms * 0.65:
                self.smooth_head_dir[0] = self.smooth_head_dir[0] * 0.4 + dx * 0.6
                self.smooth_head_dir[1] = self.smooth_head_dir[1] * 0.4 + dy * 0.6
            return True
        return False

    def toggle_pause(self) -> bool:
        if self.state in ("PLAYING", "WAITING"):
            self.state_before_pause = self.state
            self.state = "PAUSED"
            self.audio.play_click()
            return True
        if self.state == "PAUSED":
            self.state = self.state_before_pause
            self.audio.play_click()
            return True
        return False

    def resume(self) -> bool:
        if self.state == "PAUSED":
            self.state = self.state_before_pause
            self.audio.play_click()
            return True
        return False

    def trigger_death(self, reason: str = "collision") -> None:
        if self.state in ("DYING", "GAMEOVER", "WON"):
            return
        self.death_reason = reason
        self.smooth_head_dir = [float(self.direction["x"]), float(self.direction["y"])]
        self.death_progress = 1.0
        self.state = "DYING"
        self.dying_timer_ms = 0.0
        self.mouth_anim = 0.0
        self.eating_apple = None
        self.high_score = self.settings_manager.record_score(self.score)
        self.audio.play_die()

    def trigger_win(self) -> None:
        self.state = "WON"
        self.high_score = self.settings_manager.record_score(self.score)
        self.audio.play_win()

    def award_point(self, cell_x: int, cell_y: int, grow_main_snake: bool) -> None:
        self.score += 1
        self.high_score = self.settings_manager.record_score(self.score)
        self.audio.play_eat()
        if grow_main_snake:
            self.just_grew = True
        self.bulges.append(6.0)

        cx, cy = self.cell_center_px({"x": cell_x, "y": cell_y})
        for _ in range(8):
            ang = self.rand() * math.pi * 2.0
            spd = 55.0 + self.rand() * 70.0
            self.particles.append({
                "x": cx,
                "y": cy,
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd,
                "r": 2.5 + self.rand() * 2.0,
                "life": 1.0,
            })

    def _poll_held_diagonal(self) -> None:
        if self.state != "PLAYING" or self.input_queue or not self._moved_since_keydown:
            return
        held = []
        if "UP" in self.held_dirs:
            held.append({"x": 0, "y": -1})
        elif "DOWN" in self.held_dirs:
            held.append({"x": 0, "y": 1})
        if "LEFT" in self.held_dirs:
            held.append({"x": -1, "y": 0})
        elif "RIGHT" in self.held_dirs:
            held.append({"x": 1, "y": 0})

        if len(held) == 2:
            if held[0] == self.direction:
                other = held[1]
            elif held[1] == self.direction:
                other = held[0]
            else:
                return
            if not (other["x"] == -self.direction["x"] and other["y"] == -self.direction["y"]):
                self.input_queue.append(other)

    def step_once(self) -> None:
        if self.state != "PLAYING":
            return

        ModeEngine.on_before_step(self)
        next_dir = self.input_queue.pop(0) if self.input_queue else self.direction
        head = self.snake[0]
        dest = ModeEngine.resolve_step_position(self, head["x"] + next_dir["x"], head["y"] + next_dir["y"])

        if dest["hit_wall"]:
            self.direction = next_dir
            self.trigger_death("wall")
            return

        dx, dy = dest["x"], dest["y"]
        obs = ModeEngine.check_obstacle_and_crate(self, dx, dy, next_dir)
        if obs["fatal"]:
            self.direction = next_dir
            self.trigger_death(obs["reason"])
            return

        is_dim = ModeEngine.has(self, "dimension")
        food_idx = next(
            (
                i for i, f in enumerate(self.foods)
                if f["x"] == dx and f["y"] == dy and (not is_dim or f["dimension"] == self.active_dimension)
            ),
            -1,
        )
        will_grow = (food_idx != -1) or bool(obs.get("scored_crate"))

        if ModeEngine.check_self_collision(self, dx, dy, self.snake, will_grow):
            self.direction = next_dir
            self.trigger_death("self")
            return

        if ModeEngine.has(self, "yinyang") and self.yin_yang_snake and not ModeEngine.has(self, "peace"):
            if any(s["x"] == dx and s["y"] == dy for s in self.yin_yang_snake):
                self.direction = next_dir
                self.trigger_death("yinyang_collision")
                return

        self.direction = next_dir
        self.prev_tail = {"x": self.snake[-1]["x"], "y": self.snake[-1]["y"]}
        self.snake.insert(0, {"x": dx, "y": dy})
        self.step_count += 1
        self._moved_since_keydown = True

        if food_idx != -1:
            eaten_food = self.foods[food_idx]
            self.just_grew = True
            self.award_point(eaten_food["x"], eaten_food["y"], True)

            cx, cy = self.cell_center_px(eaten_food)
            self.eating_apple = {
                "start_x": cx,
                "start_y": cy,
                "x": cx,
                "y": cy,
                "sprite": eaten_food["sprite"],
                "scale": 1.0,
                "timer_ms": 0.0,
                "duration_ms": self.move_interval_ms * 0.95,
            }

            ModeEngine.on_eat_food(self, eaten_food, food_idx)

            if len(self.snake) >= self.cols * self.rows:
                self.trigger_win()
                return

            if not ModeEngine.ensure_foods(self, False):
                self.trigger_win()
                return
        elif obs.get("scored_crate"):
            self.just_grew = True
        else:
            self.just_grew = False
            self.snake.pop()

        ModeEngine.on_after_step(self)

    def update(self, dt_ms: float) -> None:
        # CRITICAL PAUSE INVARIANT: freeze 100% of state, timers, and animations while PAUSED
        if self.state == "PAUSED":
            return

        clamped_ms = min(50.0, max(0.0, float(dt_ms)))
        dt_sec = clamped_ms / 1000.0

        if self.state in ("WAITING", "MENU"):
            self.game_time_ms += clamped_ms
            for f in self.foods:
                if f["spawn_scale"] < 1.0:
                    f["spawn_scale"] = min(1.0, f["spawn_scale"] + dt_sec * 5.0)
            return

        if self.state == "PLAYING":
            self.game_time_ms += clamped_ms
            self.elapsed_ms += clamped_ms
            self._poll_held_diagonal()

            self.move_timer_ms += clamped_ms
            while self.move_timer_ms >= self.move_interval_ms and self.state == "PLAYING":
                self.move_timer_ms -= self.move_interval_ms
                self.step_once()

            if self.state == "PLAYING":
                ModeEngine.on_update_continuous(self, clamped_ms)
        elif self.state == "DYING":
            self.dying_timer_ms += clamped_ms
            if self.dying_timer_ms >= self.dying_duration_ms:
                self.state = "GAMEOVER"

        if self.state == "PLAYING":
            lerp = min(1.0, dt_sec * 32.0)
            self.smooth_head_dir[0] += (self.direction["x"] - self.smooth_head_dir[0]) * lerp
            self.smooth_head_dir[1] += (self.direction["y"] - self.smooth_head_dir[1]) * lerp

        if self.state in ("DYING", "GAMEOVER"):
            recoil_p = min(1.0, (self.dying_timer_ms / 1000.0) / 0.18)
            self.recoil_px = math.sin(recoil_p * (math.pi / 2.0)) * 12.0
        else:
            self.recoil_px = 0.0

        hx, hy = self.get_interpolated_head_px()
        ndx, ndy = self.get_normalized_head_dir()

        if self.eating_apple is not None:
            self.eating_apple["timer_ms"] += clamped_ms
            p = min(1.0, self.eating_apple["timer_ms"] / self.eating_apple["duration_ms"])
            mx = hx + ndx * (self.cell_size * 0.26)
            my = hy + ndy * (self.cell_size * 0.26)
            self.eating_apple["x"] = self.eating_apple["start_x"] * (1.0 - p) + mx * p
            self.eating_apple["y"] = self.eating_apple["start_y"] * (1.0 - p) + my * p
            self.eating_apple["scale"] = 1.0 if p < 0.45 else max(0.0, 1.0 - ((p - 0.45) / 0.55))
            if p >= 1.0:
                self.eating_apple = None

        for f in self.foods:
            if f["spawn_scale"] < 1.0:
                f["spawn_scale"] = min(1.0, f["spawn_scale"] + dt_sec * 5.0)
        for p_item in self.poisons:
            if p_item["spawn_scale"] < 1.0:
                p_item["spawn_scale"] = min(1.0, p_item["spawn_scale"] + dt_sec * 5.0)

        if self.bulges and self.state == "PLAYING":
            max_body_px = max(1, len(self.snake) - 1) * self.cell_size
            self.bulges = [b + 260.0 * dt_sec for b in self.bulges if b + 260.0 * dt_sec < max_body_px]

        for part in self.particles:
            part["x"] += part["vx"] * dt_sec
            part["y"] += part["vy"] * dt_sec
            part["life"] -= dt_sec * 3.0
        self.particles = [p for p in self.particles if p["life"] > 0]

        if self.state in ("DYING", "GAMEOVER", "WON"):
            self.mouth_anim = 0.0
        elif self.eating_apple is not None:
            p = self.eating_apple["timer_ms"] / self.eating_apple["duration_ms"]
            target = 1.0 if p < 0.55 else 0.0
            self.mouth_anim += (target - self.mouth_anim) * min(1.0, dt_sec * 22.0)
        else:
            nearest = self.get_nearest_food_px(hx, hy)
            dist = math.hypot(hx - nearest[0], hy - nearest[1]) if nearest is not None else float("inf")
            target = 1.0 if dist < self.cell_size * 2.5 else 0.0
            self.mouth_anim += (target - self.mouth_anim) * min(1.0, dt_sec * 14.0)

    def get_move_progress(self) -> float:
        if self.state == "PLAYING":
            return min(1.0, self.move_timer_ms / self.move_interval_ms)
        if self.state == "PAUSED":
            if self.state_before_pause in ("WAITING", "MENU"):
                return 1.0
            return min(1.0, self.move_timer_ms / self.move_interval_ms)
        if self.state in ("DYING", "GAMEOVER"):
            return self.death_progress
        return 1.0

    def get_normalized_head_dir(self) -> Tuple[float, float]:
        length = math.hypot(self.smooth_head_dir[0], self.smooth_head_dir[1])
        if length > 0.001:
            return (self.smooth_head_dir[0] / length, self.smooth_head_dir[1] / length)
        return (float(self.direction["x"]), float(self.direction["y"]))

    def get_interpolated_head_px(self) -> Tuple[float, float]:
        p0 = self.cell_center_px(self.snake[0])
        if len(self.snake) < 2:
            return p0
        p1 = self.cell_center_px(self.snake[1])
        if math.hypot(p0[0] - p1[0], p0[1] - p1[1]) > self.cell_size * 1.5:
            return p0
        prog = self.get_move_progress()
        return (p1[0] + (p0[0] - p1[0]) * prog, p1[1] + (p0[1] - p1[1]) * prog)

    def get_nearest_food_px(self, rx: float, ry: float) -> Optional[Tuple[float, float]]:
        best = None
        best_dist = float("inf")
        is_dim = ModeEngine.has(self, "dimension")
        for f in self.foods:
            if is_dim and f["dimension"] != self.active_dimension:
                continue
            cx, cy = self.cell_center_px(f)
            d = math.hypot(cx - rx, cy - ry)
            if d < best_dist:
                best_dist = d
                best = (cx, cy)
        return best
