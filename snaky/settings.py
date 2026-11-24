"""Snaky Game — Persistent Settings & High-Score Manager (local JSON in data/)."""

import copy
import json
import os
import random
from typing import Callable, Dict, List, Optional

from . import constants as C
from .paths import get_data_dir

DEFAULT_SETTINGS = {
    "mode": "classic",
    "blender_modes": ["wall", "portal"],
    "speed": "snake",
    "board_size": "regular",
    "food_count": "1",
    "food_type": "apple",
    "snake_color": "blue",
    "theme": "classic",
    "graphics_style": "smooth",
    "muted": False,
    "show_timer": False,
}


class SettingsManager:
    """Loads, validates, updates, and persists settings and per-config high scores."""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = data_dir if data_dir is not None else get_data_dir()
        os.makedirs(self.data_dir, exist_ok=True)
        self.settings_path = os.path.join(self.data_dir, "settings.json")
        self.scores_path = os.path.join(self.data_dir, "highscores.json")
        # Legacy compatibility with older single-value highscore.json if present
        self.legacy_score_path = os.path.join(self.data_dir, "highscore.json")

        self.settings = self._load_settings()
        self.high_scores = self._load_high_scores()

    def sanitize(self, raw: Optional[Dict]) -> Dict:
        s = copy.deepcopy(DEFAULT_SETTINGS)
        if isinstance(raw, dict):
            s.update(raw)

        if s["mode"] not in C.MODE_MAP:
            s["mode"] = DEFAULT_SETTINGS["mode"]

        bm = s.get("blender_modes")
        if not isinstance(bm, list):
            bm = list(DEFAULT_SETTINGS["blender_modes"])
        else:
            seen = []
            for mid in bm:
                if mid in C.MODE_MAP and C.MODE_MAP[mid]["blendable"] and mid not in seen:
                    seen.append(mid)
            bm = seen if len(seen) >= 2 else list(DEFAULT_SETTINGS["blender_modes"])
        s["blender_modes"] = bm

        if s["speed"] not in C.SPEEDS:
            s["speed"] = DEFAULT_SETTINGS["speed"]
        if s["board_size"] not in C.BOARD_SIZES:
            s["board_size"] = DEFAULT_SETTINGS["board_size"]
        if s["food_count"] not in C.FOOD_COUNTS:
            s["food_count"] = DEFAULT_SETTINGS["food_count"]
        if s["food_type"] not in C.FOOD_TYPES:
            s["food_type"] = DEFAULT_SETTINGS["food_type"]
        if s["snake_color"] not in C.SNAKE_COLORS:
            s["snake_color"] = DEFAULT_SETTINGS["snake_color"]
        if s["theme"] not in C.THEMES:
            s["theme"] = DEFAULT_SETTINGS["theme"]
        if s["graphics_style"] not in C.GRAPHICS_STYLES:
            s["graphics_style"] = DEFAULT_SETTINGS["graphics_style"]

        s["muted"] = bool(s["muted"])
        s["show_timer"] = bool(s["show_timer"])
        return s

    def _load_settings(self) -> Dict:
        if os.path.isfile(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    return self.sanitize(json.load(f))
            except Exception:
                pass
        s = self.sanitize(DEFAULT_SETTINGS)
        self._save_settings(s)
        return s

    def _save_settings(self, s: Optional[Dict] = None) -> None:
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(s if s is not None else self.settings, f, indent=2)
        except Exception:
            pass

    def get(self) -> Dict:
        res = dict(self.settings)
        res["blender_modes"] = list(self.settings["blender_modes"])
        return res

    def update(self, **patch) -> Dict:
        merged = self.get()
        merged.update(patch)
        self.settings = self.sanitize(merged)
        self._save_settings()
        return self.get()

    def reset(self) -> Dict:
        self.settings = self.sanitize(DEFAULT_SETTINGS)
        self._save_settings()
        return self.get()

    def randomize(self, rng: Optional[Callable[[], float]] = None) -> Dict:
        rand = rng or random.random

        def pick(seq):
            return seq[int(rand() * len(seq)) % len(seq)]

        mode_ids = [m["id"] for m in C.MODES]
        blend_ids = [m["id"] for m in C.BLENDABLE_MODES]
        b1 = pick(blend_ids)
        b2 = pick([m for m in blend_ids if m != b1])

        return self.update(
            mode=pick(mode_ids),
            blender_modes=[b1, b2],
            food_type=pick(C.FOOD_TYPE_ORDER),
            food_count=pick(C.FOOD_COUNT_ORDER),
            speed=pick(C.SPEED_ORDER),
            board_size=pick(C.BOARD_SIZE_ORDER),
            snake_color=pick(C.SNAKE_COLOR_ORDER),
            theme=pick(C.THEME_ORDER),
            graphics_style=pick(C.GRAPHICS_STYLE_ORDER),
        )

    def get_active_modes(self) -> List[str]:
        if self.settings["mode"] == "blender":
            return list(self.settings["blender_modes"])
        return [self.settings["mode"]]

    def get_score_key(self) -> str:
        if self.settings["mode"] == "blender":
            mode_part = "blender:" + "+".join(sorted(self.settings["blender_modes"]))
        else:
            mode_part = self.settings["mode"]
        return f"{mode_part}|{self.settings['board_size']}|{self.settings['speed']}|{self.settings['food_count']}"

    def _load_high_scores(self) -> Dict:
        if os.path.isfile(self.scores_path):
            try:
                with open(self.scores_path, "r", encoding="utf-8") as f:
                    parsed = json.load(f)
                    if isinstance(parsed, dict):
                        return {
                            "global": int(parsed.get("global", 0)),
                            "by_config": dict(parsed.get("by_config", {})),
                        }
            except Exception:
                pass

        # Import legacy highscore.json if user had an existing score
        legacy_val = 0
        if os.path.isfile(self.legacy_score_path):
            try:
                with open(self.legacy_score_path, "r", encoding="utf-8") as f:
                    legacy_val = int(json.load(f).get("high_score", 0))
            except Exception:
                legacy_val = 0

        data = {"global": legacy_val, "by_config": {}}
        if legacy_val > 0:
            data["by_config"]["classic|regular|snake|1"] = legacy_val
        self._save_high_scores(data)
        return data

    def _save_high_scores(self, data: Optional[Dict] = None) -> None:
        payload = data if data is not None else self.high_scores
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.scores_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            # Also keep data/highscore.json synced with global high score
            with open(self.legacy_score_path, "w", encoding="utf-8") as f:
                json.dump({"high_score": int(payload.get("global", 0))}, f)
        except Exception:
            pass

    def get_high_score(self) -> int:
        key = self.get_score_key()
        return int(self.high_scores.get("by_config", {}).get(key, 0))

    def get_global_high_score(self) -> int:
        return int(self.high_scores.get("global", 0))

    def record_score(self, score: int) -> int:
        key = self.get_score_key()
        by_cfg = self.high_scores.setdefault("by_config", {})
        updated = False
        if score > int(by_cfg.get(key, 0)):
            by_cfg[key] = int(score)
            updated = True
        if score > int(self.high_scores.get("global", 0)):
            self.high_scores["global"] = int(score)
            updated = True
        if updated:
            self._save_high_scores()
        return self.get_high_score()
