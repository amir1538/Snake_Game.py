"""Snaky Game — Automated Regression Test Suite (rea-ci-tests-audit).

Run with:
    python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
import wave

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from snaky import constants as C
from snaky.audio import (
    NullAudioManager,
    _make_click_samples,
    _make_die_samples,
    _make_move_pop_samples,
    _samples_to_wav_bytes,
)
from snaky.engine import GameEngine
from snaky.paths import get_asset_path
from snaky.settings import SettingsManager


def make_deterministic_rng(seed: int = 42):
    state = [seed]

    def _rng() -> float:
        state[0] = (state[0] * 16807) % 2147483647
        return (state[0] - 1) / 2147483646.0

    return _rng


class TestSnakyGame(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_env(self, seed: int = 42, **patch):
        sm = SettingsManager(data_dir=self.data_dir)
        if patch:
            sm.update(**patch)
        audio = NullAudioManager(muted=True)
        engine = GameEngine(sm, audio, rng=make_deterministic_rng(seed))
        return sm, audio, engine

    # --- 1. Startup, Settings & Persistence ---
    def test_01_startup_menu_and_waiting(self):
        _, _, engine = self._make_env()
        self.assertEqual(engine.state, "MENU")
        engine.start_from_menu()
        self.assertEqual(engine.state, "WAITING")
        self.assertEqual(engine.cols, 17)
        self.assertEqual(engine.rows, 15)
        self.assertEqual(len(engine.snake), 3)
        self.assertGreaterEqual(len(engine.foods), 1)

    def test_02_settings_json_persistence(self):
        sm1 = SettingsManager(data_dir=self.data_dir)
        sm1.update(
            mode="wall",
            speed="rabbit",
            board_size="big",
            food_count="5",
            food_type="pineapple",
            snake_color="cyan",
            theme="winter",
            graphics_style="pixel",
            show_timer=True,
            muted=True,
        )
        sm2 = SettingsManager(data_dir=self.data_dir)
        s = sm2.get()
        self.assertEqual(s["mode"], "wall")
        self.assertEqual(s["speed"], "rabbit")
        self.assertEqual(s["board_size"], "big")
        self.assertEqual(s["food_count"], "5")
        self.assertEqual(s["food_type"], "pineapple")
        self.assertEqual(s["snake_color"], "cyan")
        self.assertEqual(s["theme"], "winter")
        self.assertEqual(s["graphics_style"], "pixel")
        self.assertTrue(s["show_timer"])
        self.assertTrue(s["muted"])

    def test_03_highscores_persistence_and_legacy_sync(self):
        sm1 = SettingsManager(data_dir=self.data_dir)
        sm1.record_score(15)
        sm1.update(mode="noborders")
        sm1.record_score(7)

        sm2 = SettingsManager(data_dir=self.data_dir)
        self.assertEqual(sm2.get_high_score(), 7)
        self.assertEqual(sm2.get_global_high_score(), 15)
        sm2.update(mode="classic")
        self.assertEqual(sm2.get_high_score(), 15)
        self.assertTrue(os.path.isfile(os.path.join(self.data_dir, "highscore.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.data_dir, "highscores.json")))

    def test_04_dice_randomize_and_sanitize(self):
        sm = SettingsManager(data_dir=self.data_dir)
        s = sm.randomize(rng=make_deterministic_rng(99))
        self.assertIn(s["mode"], C.MODE_MAP)
        self.assertIn(s["food_type"], C.FOOD_TYPES)
        self.assertIn(s["theme"], C.THEMES)
        self.assertIn(s["graphics_style"], C.GRAPHICS_STYLES)
        self.assertGreaterEqual(len(s["blender_modes"]), 2)

        # Invalid values sanitize cleanly back to defaults
        clean = sm.sanitize({"mode": "invalid", "speed": "warp", "blender_modes": ["wall"]})
        self.assertEqual(clean["mode"], "classic")
        self.assertEqual(clean["speed"], "snake")
        self.assertEqual(len(clean["blender_modes"]), 2)

    # --- 2. Controls, Zero-Latency Input & Core Gameplay ---
    def test_05_immediate_first_step_3_turn_buffer_and_180_guard(self):
        _, _, engine = self._make_env()
        start_x = engine.snake[0]["x"]
        self.assertTrue(engine.queue_direction(1, 0))
        self.assertEqual(engine.state, "PLAYING")
        self.assertEqual(engine.snake[0]["x"], start_x + 1)
        self.assertFalse(engine.queue_direction(-1, 0))
        self.assertTrue(engine.queue_direction(0, -1))
        self.assertTrue(engine.queue_direction(-1, 0))
        self.assertTrue(engine.queue_direction(0, 1))
        self.assertEqual(len(engine.input_queue), 3)

    def test_06_classic_eat_growth_bulge_and_eating_anim(self):
        _, _, engine = self._make_env(mode="classic")
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.foods = [{"x": h["x"] + 1, "y": h["y"], "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False}]
        engine.step_once()
        self.assertEqual(engine.score, 1)
        self.assertEqual(len(engine.snake), 4)
        self.assertIsNotNone(engine.eating_apple)
        self.assertGreater(len(engine.bulges), 0)

    def test_07_wall_collision_dying_gameover_and_restart(self):
        _, _, engine = self._make_env(mode="classic", board_size="small")
        engine.queue_direction(1, 0)
        engine.snake = [{"x": engine.cols - 1, "y": 4}, {"x": engine.cols - 2, "y": 4}, {"x": engine.cols - 3, "y": 4}]
        engine.step_once()
        self.assertEqual(engine.state, "DYING")
        self.assertEqual(engine.death_reason, "wall")
        for _ in range(30):
            engine.update(40.0)
        self.assertEqual(engine.state, "GAMEOVER")
        engine.reset(show_menu=False)
        self.assertEqual(engine.state, "WAITING")
        self.assertEqual(engine.score, 0)

    # --- 3. CRITICAL: ESC Pause / Continue Complete Freeze ---
    def test_08_esc_pause_freezes_everything_and_resumes_cleanly(self):
        _, _, engine = self._make_env(mode="minesweeper")
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.foods = [{"x": h["x"] + 1, "y": h["y"], "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False}]
        engine.step_once()
        engine.mines = [{"x": engine.snake[0]["x"] + 1, "y": engine.snake[0]["y"], "max_timer_ms": 2500.0, "timer_ms": 2000.0, "triggered": True}]
        engine.update(40.0)

        snap = (
            engine.snake[0]["x"],
            engine.snake[0]["y"],
            engine.score,
            engine.elapsed_ms,
            engine.game_time_ms,
            engine.bulges[0],
            engine.eating_apple["timer_ms"] if engine.eating_apple else None,
            engine.mines[0]["timer_ms"],
        )

        engine.toggle_pause()
        self.assertEqual(engine.state, "PAUSED")
        for _ in range(60):
            engine.update(50.0)

        after = (
            engine.snake[0]["x"],
            engine.snake[0]["y"],
            engine.score,
            engine.elapsed_ms,
            engine.game_time_ms,
            engine.bulges[0],
            engine.eating_apple["timer_ms"] if engine.eating_apple else None,
            engine.mines[0]["timer_ms"],
        )
        self.assertEqual(after, snap)

        engine.resume()
        self.assertEqual(engine.state, "PLAYING")
        engine.update(40.0)
        self.assertGreater(engine.elapsed_ms, snap[3])
        self.assertGreater(engine.game_time_ms, snap[4])

    # --- 4. Board Size Propagation ---
    def test_09_board_size_updates_dimensions_bounds_and_food(self):
        sm, _, engine = self._make_env(board_size="small")
        self.assertEqual((engine.cols, engine.rows), (10, 9))
        for f in engine.foods:
            self.assertTrue(0 <= f["x"] < 10 and 0 <= f["y"] < 9)

        sm.update(board_size="big")
        engine.apply_settings_and_reset(False)
        self.assertEqual((engine.cols, engine.rows), (24, 21))
        engine.state = "PLAYING"
        engine.snake = [{"x": 23, "y": 10}, {"x": 22, "y": 10}, {"x": 21, "y": 10}]
        engine.direction = {"x": 1, "y": 0}
        engine.step_once()
        self.assertEqual(engine.state, "DYING")

    # --- 5. All Remaining 16 Game Modes + Blender ---
    def test_10_wall_mode(self):
        _, _, engine = self._make_env(mode="wall")
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.foods = [{"x": h["x"] + 1, "y": h["y"], "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False}]
        engine.step_once()
        self.assertEqual(len(engine.walls), 1)
        engine.walls.append({"x": engine.snake[0]["x"] + 1, "y": engine.snake[0]["y"]})
        engine.step_once()
        self.assertEqual(engine.state, "DYING")
        self.assertEqual(engine.death_reason, "wall_obstacle")

    def test_11_portal_mode(self):
        _, _, engine = self._make_env(mode="portal", food_count="1")
        self.assertGreaterEqual(len(engine.foods), 2)
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.foods = [
            {"x": h["x"] + 1, "y": h["y"], "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False},
            {"x": 12, "y": 2, "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False},
        ]
        engine.step_once()
        self.assertEqual((engine.snake[0]["x"], engine.snake[0]["y"]), (12, 2))

    def test_12_cheese_mode(self):
        _, _, engine = self._make_env(mode="cheese")
        engine.queue_direction(0, 1)
        engine.snake = [{"x": 5, "y": 5}, {"x": 5, "y": 6}, {"x": 4, "y": 6}, {"x": 4, "y": 5}]
        engine.direction = {"x": 0, "y": 1}
        engine.foods = [{"x": 10, "y": 10, "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False}]
        engine.step_once()
        self.assertEqual(engine.state, "PLAYING")

    def test_13_noborders_mode(self):
        _, _, engine = self._make_env(mode="noborders")
        engine.queue_direction(1, 0)
        engine.snake = [{"x": engine.cols - 1, "y": 5}, {"x": engine.cols - 2, "y": 5}, {"x": engine.cols - 3, "y": 5}]
        engine.step_once()
        self.assertEqual(engine.state, "PLAYING")
        self.assertEqual(engine.snake[0]["x"], 0)

    def test_14_twin_mode(self):
        _, _, engine = self._make_env(mode="twin")
        engine.queue_direction(1, 0)
        engine.snake = [{"x": 5, "y": 5}, {"x": 4, "y": 5}, {"x": 3, "y": 5}]
        engine.foods = [{"x": 6, "y": 5, "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False}]
        engine.step_once()
        self.assertEqual(engine.snake[0]["x"], 3)
        self.assertEqual(engine.direction["x"], -1)

    def test_15_winged_mode(self):
        _, _, engine = self._make_env(mode="winged")
        engine.queue_direction(1, 0)
        engine.foods = [{"x": 10, "y": 7, "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False}]
        engine.wing_tick_counter = 0
        engine.step_once()
        engine.step_once()
        self.assertEqual(engine.foods[0]["x"], 11)

    def test_16_yinyang_mode(self):
        _, _, engine = self._make_env(mode="yinyang")
        self.assertIsNotNone(engine.yin_yang_snake)
        init_x = engine.yin_yang_snake[0]["x"]
        engine.queue_direction(1, 0)
        self.assertEqual(engine.yin_yang_snake[0]["x"], init_x - 1)

    def test_17_key_mode(self):
        _, _, engine = self._make_env(mode="key")
        self.assertEqual(len(engine.keys), 1)
        self.assertEqual(len(engine.locks), 1)
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.keys[0]["x"], engine.keys[0]["y"] = h["x"] + 1, h["y"]
        lx, ly = engine.locks[0]["x"], engine.locks[0]["y"]
        engine.step_once()
        self.assertTrue(any(f["x"] == lx and f["y"] == ly and f["is_bonus"] for f in engine.foods))

    def test_18_sokoban_mode_and_non_scoring_regression(self):
        _, _, engine = self._make_env(mode="sokoban")
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.crates = [{"x": h["x"] + 1, "y": h["y"], "pair_id": 99}]
        engine.targets = [{"x": h["x"] + 2, "y": h["y"], "pair_id": 99}]
        engine.step_once()
        self.assertEqual(engine.score, 1)

        # Regression: pushing crate NOT onto target right after growing must not falsely grow
        engine.just_grew = True
        h = engine.snake[0]
        len_before = len(engine.snake)
        engine.crates = [{"x": h["x"] + 1, "y": h["y"], "pair_id": 100}]
        engine.targets = [{"x": 1, "y": 1, "pair_id": 100}]
        engine.foods = [{"x": 12, "y": 12, "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False}]
        engine.step_once()
        self.assertEqual(len(engine.snake), len_before)

    def test_19_poison_mode(self):
        _, _, engine = self._make_env(mode="poison")
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.poisons = [{"x": h["x"] + 1, "y": h["y"], "spawn_scale": 1.0}]
        engine.step_once()
        self.assertGreater(engine.poison_steps_remaining, 0)

    def test_20_dimension_mode(self):
        _, _, engine = self._make_env(mode="dimension")
        self.assertEqual(engine.active_dimension, 0)
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.foods = [
            {"x": h["x"] + 1, "y": h["y"], "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False},
            {"x": 12, "y": 12, "sprite": "apple", "dimension": 1, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False},
        ]
        engine.step_once()
        self.assertEqual(engine.active_dimension, 1)

    def test_21_minesweeper_mode(self):
        _, _, engine = self._make_env(mode="minesweeper")
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.mines = [{"x": h["x"] + 1, "y": h["y"] + 1, "max_timer_ms": 200.0, "timer_ms": 200.0, "triggered": False}]
        for _ in range(6):
            engine.update(45.0)
        self.assertEqual(engine.state, "DYING")
        self.assertEqual(engine.death_reason, "mine_countdown")

    def test_22_statue_mode(self):
        _, _, engine = self._make_env(mode="statue")
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.foods = [{"x": h["x"] + 1, "y": h["y"], "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False}]
        engine.step_once()
        self.assertGreaterEqual(len(engine.statues), 2)
        self.assertEqual(len(engine.snake), 2)

    def test_23_light_mode(self):
        _, _, engine = self._make_env(mode="light")
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.foods = [{"x": h["x"] + 1, "y": h["y"], "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False}]
        engine.step_once()
        self.assertGreater(engine.light_radius, 4.5)
        self.assertGreater(len(engine.light_pulses), 0)

    def test_24_peace_mode(self):
        _, _, engine = self._make_env(mode="peace")
        engine.queue_direction(1, 0)
        engine.snake = [{"x": engine.cols - 1, "y": 5}, {"x": engine.cols - 2, "y": 5}, {"x": engine.cols - 3, "y": 5}]
        engine.step_once()
        self.assertEqual(engine.state, "PLAYING")

    def test_25_blender_mode(self):
        _, _, engine = self._make_env(mode="blender", blender_modes=["wall", "noborders"])
        engine.queue_direction(1, 0)
        h = engine.snake[0]
        engine.foods = [{"x": h["x"] + 1, "y": h["y"], "sprite": "apple", "dimension": 0, "vx": 1, "vy": 0, "spawn_scale": 1.0, "is_bonus": False}]
        engine.step_once()
        self.assertEqual(len(engine.walls), 1)
        engine.snake = [{"x": engine.cols - 1, "y": 2}, {"x": engine.cols - 2, "y": 2}, {"x": engine.cols - 3, "y": 2}]
        engine.walls = []
        engine.step_once()
        self.assertEqual(engine.snake[0]["x"], 0)
        self.assertEqual(engine.state, "PLAYING")

    # --- 6. Audio Assets & Synthesis Integrity ---
    def test_26_audio_assets_and_synthesizers(self):
        eat_wav = get_asset_path("sound", "eat_apple.wav")
        self.assertTrue(os.path.isfile(eat_wav), "assets/sound/eat_apple.wav must exist")
        with wave.open(eat_wav, "rb") as wf:
            self.assertGreater(wf.getnframes(), 0)
            self.assertEqual(wf.getframerate(), 48000)

        for samples in (_make_move_pop_samples(262.0, 215.0, 0.060), _make_die_samples(), _make_click_samples()):
            self.assertGreater(len(samples), 100)
            self.assertTrue(all(-32767 <= s <= 32767 for s in samples))
            buf = _samples_to_wav_bytes(samples)
            with wave.open(buf, "rb") as wf:
                self.assertEqual(wf.getnframes(), len(samples))


if __name__ == "__main__":
    unittest.main()
