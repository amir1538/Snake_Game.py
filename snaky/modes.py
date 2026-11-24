"""Snaky Game — Composable Game Mode Engine (All 17 Modes + Blender Composition)."""

from typing import Callable, Dict, List, Optional, Set, Tuple

from . import constants as C


class ModeEngine:
    """Stateless composable rule hooks matching approved js/modes.js 1:1."""

    @staticmethod
    def has(engine, mode_id: str) -> bool:
        return mode_id in engine.active_modes

    @staticmethod
    def get_occupied_set(engine, include_extras=None) -> Set[Tuple[int, int]]:
        occ: Set[Tuple[int, int]] = set()
        for s in engine.snake:
            occ.add((s["x"], s["y"]))
        if engine.yin_yang_snake:
            for s in engine.yin_yang_snake:
                occ.add((s["x"], s["y"]))
        for f in engine.foods:
            occ.add((f["x"], f["y"]))
        for w in engine.walls:
            occ.add((w["x"], w["y"]))
        for st in engine.statues:
            occ.add((st["x"], st["y"]))
        for m in engine.mines:
            occ.add((m["x"], m["y"]))
        for k in engine.keys:
            occ.add((k["x"], k["y"]))
        for lk in engine.locks:
            occ.add((lk["x"], lk["y"]))
        for c in engine.crates:
            occ.add((c["x"], c["y"]))
        for t in engine.targets:
            occ.add((t["x"], t["y"]))
        for p in engine.poisons:
            occ.add((p["x"], p["y"]))
        if include_extras:
            for ex in include_extras:
                occ.add((ex["x"], ex["y"]))
        return occ

    @classmethod
    def find_free_cell(
        cls,
        engine,
        predicate: Optional[Callable[[int, int], bool]] = None,
    ) -> Optional[Dict[str, int]]:
        occ = cls.get_occupied_set(engine)
        candidates = []
        for y in range(engine.rows):
            for x in range(engine.cols):
                if (x, y) not in occ:
                    if predicate is None or predicate(x, y):
                        candidates.append({"x": x, "y": y})
        if not candidates:
            return None
        idx = int(engine.rand() * len(candidates)) % len(candidates)
        return candidates[idx]

    @staticmethod
    def pick_food_sprite(engine) -> str:
        ftype = engine.settings["food_type"]
        if ftype == "random":
            keys = C.CONCRETE_FOOD_KEYS
            return keys[int(engine.rand() * len(keys)) % len(keys)]
        return ftype

    @classmethod
    def init_mode_state(cls, engine) -> None:
        engine.walls = []
        engine.statues = []
        engine.mines = []
        engine.keys = []
        engine.locks = []
        engine.crates = []
        engine.targets = []
        engine.poisons = []
        engine.active_dimension = 0
        engine.poison_steps_remaining = 0
        engine.light_radius = 3.5
        engine.light_pulses = []
        engine.wing_tick_counter = 0
        engine.yin_yang_snake = None
        engine.yin_yang_prev_tail = None
        engine.yin_yang_dir = {"x": -1, "y": 0}
        engine.yin_yang_just_grew = False

        if cls.has(engine, "yinyang"):
            mid_y = engine.rows // 2
            start_x = max(3, engine.cols - 5)
            yy_y = min(engine.rows - 2, mid_y + 2)
            engine.yin_yang_snake = [
                {"x": start_x, "y": yy_y},
                {"x": start_x + 1, "y": yy_y},
                {"x": start_x + 2, "y": yy_y},
            ]
            engine.yin_yang_prev_tail = {"x": start_x + 2, "y": yy_y}
            engine.yin_yang_dir = {"x": -engine.direction["x"], "y": -engine.direction["y"]}
            engine.yin_yang_just_grew = False

        if cls.has(engine, "key"):
            cls.spawn_key_lock_pair(engine)

        if cls.has(engine, "sokoban"):
            cls.spawn_sokoban_pair(engine)

        if cls.has(engine, "poison"):
            cls.spawn_poison(engine)

    @classmethod
    def get_desired_food_count(cls, engine) -> int:
        fc = C.FOOD_COUNTS.get(engine.settings["food_count"], C.FOOD_COUNTS["1"])
        count = (1 + int(engine.rand() * 5) % 5) if fc["is_dice"] else fc["count"]
        if cls.has(engine, "portal") and count < 2:
            count = 2
        if cls.has(engine, "dimension") and count < 2:
            count = 2
        return count

    @classmethod
    def make_food_item(cls, engine, x: int, y: int, dim_override: Optional[int] = None) -> Dict:
        dirs = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (-1, 1), (1, -1), (-1, -1),
        ]
        vx, vy = dirs[int(engine.rand() * len(dirs)) % len(dirs)]
        return {
            "x": x,
            "y": y,
            "sprite": cls.pick_food_sprite(engine),
            "dimension": dim_override if dim_override is not None else engine.active_dimension,
            "vx": vx,
            "vy": vy,
            "spawn_scale": 0.01,
            "is_bonus": False,
        }

    @classmethod
    def ensure_foods(cls, engine, is_initial: bool) -> bool:
        target_count = cls.get_desired_food_count(engine)
        if is_initial:
            engine.foods = []
            mid_y = engine.rows // 2
            first_x = min(engine.cols - 2, int(engine.cols * 0.68))
            occ = cls.get_occupied_set(engine)
            if (first_x, mid_y) not in occ:
                f = cls.make_food_item(engine, first_x, mid_y, 0)
                f["spawn_scale"] = 1.0
                engine.foods.append(f)

        while len(engine.foods) < target_count:
            dim = engine.active_dimension
            if cls.has(engine, "dimension"):
                has0 = any(f["dimension"] == 0 for f in engine.foods)
                has1 = any(f["dimension"] == 1 for f in engine.foods)
                if not has0:
                    dim = 0
                elif not has1:
                    dim = 1
                else:
                    dim = int(engine.rand() * 2) % 2
            cell = cls.find_free_cell(engine)
            if cell is None:
                break
            item = cls.make_food_item(engine, cell["x"], cell["y"], dim)
            if is_initial:
                item["spawn_scale"] = 1.0
            engine.foods.append(item)

        if cls.has(engine, "dimension") and engine.foods:
            if not any(f["dimension"] == engine.active_dimension for f in engine.foods):
                engine.foods[0]["dimension"] = engine.active_dimension

        if cls.has(engine, "portal") and len(engine.foods) < 2:
            return False
        return len(engine.foods) > 0 or cls.has(engine, "sokoban")

    @classmethod
    def spawn_key_lock_pair(cls, engine) -> bool:
        head = engine.snake[0]
        lock_cell = cls.find_free_cell(
            engine, lambda x, y: abs(x - head["x"]) + abs(y - head["y"]) >= 3
        ) or cls.find_free_cell(engine)
        if not lock_cell:
            return False
        engine.next_entity_id += 1
        pair_id = engine.next_entity_id
        engine.locks.append({"x": lock_cell["x"], "y": lock_cell["y"], "pair_id": pair_id})

        key_cell = cls.find_free_cell(
            engine, lambda x, y: abs(x - lock_cell["x"]) + abs(y - lock_cell["y"]) >= 2
        ) or cls.find_free_cell(engine)
        if not key_cell:
            engine.locks.pop()
            return False
        engine.keys.append({"x": key_cell["x"], "y": key_cell["y"], "pair_id": pair_id})
        return True

    @classmethod
    def spawn_sokoban_pair(cls, engine) -> bool:
        crate_cell = cls.find_free_cell(
            engine, lambda x, y: 1 <= x <= engine.cols - 2 and 1 <= y <= engine.rows - 2
        )
        if not crate_cell:
            return False
        engine.next_entity_id += 1
        pair_id = engine.next_entity_id
        engine.crates.append({"x": crate_cell["x"], "y": crate_cell["y"], "pair_id": pair_id})

        target_cell = cls.find_free_cell(
            engine, lambda x, y: abs(x - crate_cell["x"]) + abs(y - crate_cell["y"]) >= 2
        ) or cls.find_free_cell(engine)
        if not target_cell:
            engine.crates.pop()
            return False
        engine.targets.append({"x": target_cell["x"], "y": target_cell["y"], "pair_id": pair_id})
        return True

    @classmethod
    def spawn_poison(cls, engine) -> None:
        head = engine.snake[0]
        cell = cls.find_free_cell(
            engine, lambda x, y: abs(x - head["x"]) + abs(y - head["y"]) >= 3
        ) or cls.find_free_cell(engine)
        if cell:
            engine.poisons.append({"x": cell["x"], "y": cell["y"], "spawn_scale": 0.01})

    @classmethod
    def spawn_wall(cls, engine) -> None:
        head = engine.snake[0]
        fx1 = head["x"] + engine.direction["x"]
        fy1 = head["y"] + engine.direction["y"]
        fx2 = head["x"] + engine.direction["x"] * 2
        fy2 = head["y"] + engine.direction["y"] * 2
        cell = cls.find_free_cell(
            engine,
            lambda x, y: (x, y) not in ((fx1, fy1), (fx2, fy2))
            and abs(x - head["x"]) + abs(y - head["y"]) >= 2,
        ) or cls.find_free_cell(engine)
        if cell:
            engine.walls.append({"x": cell["x"], "y": cell["y"]})

    @classmethod
    def spawn_mine(cls, engine) -> None:
        head = engine.snake[0]
        cell = cls.find_free_cell(
            engine, lambda x, y: max(abs(x - head["x"]), abs(y - head["y"])) >= 2
        ) or cls.find_free_cell(engine)
        if cell:
            engine.mines.append({
                "x": cell["x"],
                "y": cell["y"],
                "max_timer_ms": 2500.0,
                "timer_ms": 2500.0,
                "triggered": False,
            })

    @classmethod
    def resolve_step_position(cls, engine, x: int, y: int) -> Dict:
        wraps = cls.has(engine, "noborders") or cls.has(engine, "peace")
        if wraps:
            wx = x % engine.cols
            wy = y % engine.rows
            return {"x": wx, "y": wy, "hit_wall": False, "wrapped": (wx != x or wy != y)}
        hit_wall = x < 0 or x >= engine.cols or y < 0 or y >= engine.rows
        return {"x": x, "y": y, "hit_wall": hit_wall, "wrapped": False}

    @classmethod
    def on_before_step(cls, engine) -> None:
        if cls.has(engine, "poison") and engine.poison_steps_remaining > 0:
            engine.poison_steps_remaining -= 1
            all_dirs = [{"x": 1, "y": 0}, {"x": -1, "y": 0}, {"x": 0, "y": 1}, {"x": 0, "y": -1}]
            valid = [
                d for d in all_dirs
                if not (d["x"] == -engine.direction["x"] and d["y"] == -engine.direction["y"])
            ]
            chosen = valid[int(engine.rand() * len(valid)) % len(valid)]
            engine.input_queue = [chosen]

    @classmethod
    def check_obstacle_and_crate(cls, engine, nx: int, ny: int, d: Dict[str, int]) -> Dict:
        is_peace = cls.has(engine, "peace")

        if cls.has(engine, "sokoban"):
            crate_idx = next(
                (i for i, c in enumerate(engine.crates) if c["x"] == nx and c["y"] == ny),
                -1,
            )
            if crate_idx != -1:
                dest = cls.resolve_step_position(engine, nx + d["x"], ny + d["y"])
                dx, dy = dest["x"], dest["y"]
                blocked = (
                    dest["hit_wall"]
                    or any(w["x"] == dx and w["y"] == dy for w in engine.walls)
                    or any(st["x"] == dx and st["y"] == dy for st in engine.statues)
                    or any(lk["x"] == dx and lk["y"] == dy for lk in engine.locks)
                    or any(i != crate_idx and c["x"] == dx and c["y"] == dy for i, c in enumerate(engine.crates))
                    or any(s["x"] == dx and s["y"] == dy for s in engine.snake)
                )
                if blocked:
                    return {"fatal": not is_peace, "reason": "crate_blocked", "pushed_crate": False, "scored_crate": False}

                engine.crates[crate_idx]["x"] = dx
                engine.crates[crate_idx]["y"] = dy
                engine.audio.play_crate_push()

                scored_crate = False
                t_idx = next((i for i, t in enumerate(engine.targets) if t["x"] == dx and t["y"] == dy), -1)
                if t_idx != -1:
                    engine.crates.pop(crate_idx)
                    engine.targets.pop(t_idx)
                    engine.award_point(dx, dy, True)
                    cls.spawn_sokoban_pair(engine)
                    scored_crate = True
                return {"fatal": False, "pushed_crate": True, "scored_crate": scored_crate}

        if is_peace:
            return {"fatal": False, "pushed_crate": False, "scored_crate": False}

        if any(w["x"] == nx and w["y"] == ny for w in engine.walls):
            return {"fatal": True, "reason": "wall_obstacle"}
        if any(st["x"] == nx and st["y"] == ny for st in engine.statues):
            return {"fatal": True, "reason": "statue"}
        if any(lk["x"] == nx and lk["y"] == ny for lk in engine.locks):
            return {"fatal": True, "reason": "locked_block"}
        if any(m["x"] == nx and m["y"] == ny for m in engine.mines):
            return {"fatal": True, "reason": "mine_direct"}
        return {"fatal": False, "pushed_crate": False, "scored_crate": False}

    @classmethod
    def check_self_collision(cls, engine, nx: int, ny: int, snake_arr: List[Dict], will_grow: bool) -> bool:
        if cls.has(engine, "peace"):
            return False
        limit = len(snake_arr) if will_grow else len(snake_arr) - 1
        is_cheese = cls.has(engine, "cheese")
        for i in range(limit):
            if is_cheese and i % 2 == 1:
                continue
            if snake_arr[i]["x"] == nx and snake_arr[i]["y"] == ny:
                return True
        return False

    @classmethod
    def on_eat_food(cls, engine, eaten_food: Dict, food_idx: int) -> None:
        engine.foods.pop(food_idx)

        # 1. Portal Mode
        if cls.has(engine, "portal") and engine.foods:
            partner_idx = int(engine.rand() * len(engine.foods)) % len(engine.foods)
            partner = engine.foods.pop(partner_idx)
            engine.snake[0] = {"x": partner["x"], "y": partner["y"]}
            engine.audio.play_portal()

        # 2. Wall Mode
        if cls.has(engine, "wall"):
            cls.spawn_wall(engine)

        # 3. Twin Mode
        if cls.has(engine, "twin") and len(engine.snake) >= 2:
            engine.snake.reverse()
            nh, nn = engine.snake[0], engine.snake[1]
            dx = nh["x"] - nn["x"]
            dy = nh["y"] - nn["y"]
            if abs(dx) <= 1 and abs(dy) <= 1 and (dx != 0 or dy != 0):
                engine.direction = {"x": dx, "y": dy}
            else:
                engine.direction = {"x": -engine.direction["x"], "y": -engine.direction["y"]}
            engine.smooth_head_dir = [float(engine.direction["x"]), float(engine.direction["y"])]
            engine.input_queue = []
            engine.prev_tail = {"x": engine.snake[-1]["x"], "y": engine.snake[-1]["y"]}

        # 4. Dimension Mode
        if cls.has(engine, "dimension"):
            engine.active_dimension = 1 - engine.active_dimension
            engine.audio.play_dimension_shift()

        # 5. Minesweeper Mode
        if cls.has(engine, "minesweeper"):
            cls.spawn_mine(engine)

        # 6. Statue Mode
        if cls.has(engine, "statue") and len(engine.snake) > 2:
            frozen = engine.snake[2:]
            engine.snake = engine.snake[:2]
            for seg in frozen:
                if not any(st["x"] == seg["x"] and st["y"] == seg["y"] for st in engine.statues):
                    engine.statues.append({"x": seg["x"], "y": seg["y"]})
            engine.prev_tail = {"x": engine.snake[-1]["x"], "y": engine.snake[-1]["y"]}

        # 7. Light Mode
        if cls.has(engine, "light"):
            engine.light_radius = 5.4
            engine.light_pulses.append({"dist": 0.0})

    @classmethod
    def on_after_step(cls, engine) -> None:
        head = engine.snake[0]

        # Key Mode
        if cls.has(engine, "key"):
            k_idx = next((i for i, k in enumerate(engine.keys) if k["x"] == head["x"] and k["y"] == head["y"]), -1)
            if k_idx != -1:
                collected = engine.keys.pop(k_idx)
                l_idx = next((i for i, lk in enumerate(engine.locks) if lk["pair_id"] == collected["pair_id"]), -1)
                if l_idx != -1:
                    lock = engine.locks.pop(l_idx)
                    bonus = cls.make_food_item(engine, lock["x"], lock["y"], engine.active_dimension)
                    bonus["is_bonus"] = True
                    bonus["spawn_scale"] = 1.0
                    engine.foods.append(bonus)
                engine.audio.play_key_unlock()
                cls.spawn_key_lock_pair(engine)

        # Poison Mode
        if cls.has(engine, "poison"):
            p_idx = next((i for i, p in enumerate(engine.poisons) if p["x"] == head["x"] and p["y"] == head["y"]), -1)
            if p_idx != -1:
                engine.poisons.pop(p_idx)
                engine.poison_steps_remaining = 6
                engine.audio.play_poison()
                cls.spawn_poison(engine)

        # Winged Mode
        if cls.has(engine, "winged"):
            engine.wing_tick_counter += 1
            if engine.wing_tick_counter % 2 == 0:
                for f in engine.foods:
                    def is_blocked(tx: int, ty: int, cur=f) -> bool:
                        if tx < 0 or tx >= engine.cols or ty < 0 or ty >= engine.rows:
                            return True
                        if any(s["x"] == tx and s["y"] == ty for s in engine.snake):
                            return True
                        if engine.yin_yang_snake and any(s["x"] == tx and s["y"] == ty for s in engine.yin_yang_snake):
                            return True
                        if any(w["x"] == tx and w["y"] == ty for w in engine.walls):
                            return True
                        if any(st["x"] == tx and st["y"] == ty for st in engine.statues):
                            return True
                        if any(lk["x"] == tx and lk["y"] == ty for lk in engine.locks):
                            return True
                        if any(c["x"] == tx and c["y"] == ty for c in engine.crates):
                            return True
                        if any(o is not cur and o["x"] == tx and o["y"] == ty for o in engine.foods):
                            return True
                        return False

                    if is_blocked(f["x"] + f["vx"], f["y"]):
                        f["vx"] = -f["vx"]
                    if is_blocked(f["x"], f["y"] + f["vy"]):
                        f["vy"] = -f["vy"]
                    nx, ny = f["x"] + f["vx"], f["y"] + f["vy"]
                    if not is_blocked(nx, ny):
                        f["x"], f["y"] = nx, ny

        # Yin Yang Mode
        if cls.has(engine, "yinyang") and engine.yin_yang_snake:
            yy_dir = {"x": -engine.direction["x"], "y": -engine.direction["y"]}
            engine.yin_yang_dir = yy_dir
            yy_head = engine.yin_yang_snake[0]
            dest = cls.resolve_step_position(engine, yy_head["x"] + yy_dir["x"], yy_head["y"] + yy_dir["y"])
            dx, dy = dest["x"], dest["y"]

            is_peace = cls.has(engine, "peace")
            hit_wall = dest["hit_wall"] and not is_peace
            hit_main = (not is_peace) and any(s["x"] == dx and s["y"] == dy for s in engine.snake)
            hit_obs = (not is_peace) and (
                any(w["x"] == dx and w["y"] == dy for w in engine.walls)
                or any(st["x"] == dx and st["y"] == dy for st in engine.statues)
                or any(lk["x"] == dx and lk["y"] == dy for lk in engine.locks)
                or any(m["x"] == dx and m["y"] == dy for m in engine.mines)
            )
            is_dim = cls.has(engine, "dimension")
            yy_food_idx = next(
                (
                    i for i, f in enumerate(engine.foods)
                    if f["x"] == dx and f["y"] == dy and (not is_dim or f["dimension"] == engine.active_dimension)
                ),
                -1,
            )
            yy_will_grow = yy_food_idx != -1
            hit_yy_self = cls.check_self_collision(engine, dx, dy, engine.yin_yang_snake, yy_will_grow)

            if hit_wall or hit_main or hit_obs or hit_yy_self:
                engine.trigger_death("yinyang_collision")
                return

            engine.yin_yang_prev_tail = {
                "x": engine.yin_yang_snake[-1]["x"],
                "y": engine.yin_yang_snake[-1]["y"],
            }
            engine.yin_yang_snake.insert(0, {"x": dx, "y": dy})
            if yy_will_grow:
                engine.yin_yang_just_grew = True
                eaten = engine.foods.pop(yy_food_idx)
                engine.award_point(eaten["x"], eaten["y"], False)
                cls.ensure_foods(engine, False)
            else:
                engine.yin_yang_just_grew = False
                engine.yin_yang_snake.pop()

    @classmethod
    def on_update_continuous(cls, engine, dt_ms: float) -> None:
        dt_sec = dt_ms / 1000.0

        # Minesweeper 3x3 countdown (freezes completely when PAUSED)
        if cls.has(engine, "minesweeper") and engine.mines:
            head = engine.snake[0]
            is_peace = cls.has(engine, "peace")
            for m in engine.mines:
                dist = max(abs(head["x"] - m["x"]), abs(head["y"] - m["y"]))
                if dist <= 1:
                    m["triggered"] = True
                    m["timer_ms"] -= dt_ms
                    if m["timer_ms"] <= 0 and not is_peace:
                        m["timer_ms"] = 0.0
                        engine.trigger_death("mine_countdown")
                        return
                else:
                    m["triggered"] = False
                    m["timer_ms"] = m["max_timer_ms"]

        # Light Mode radius decay & body light pulses
        if cls.has(engine, "light"):
            base_r = 3.4
            if engine.light_radius > base_r:
                engine.light_radius = max(base_r, engine.light_radius - dt_sec * 1.4)
            max_dist = max(1, len(engine.snake) - 1) * engine.cell_size
            for lp in engine.light_pulses:
                lp["dist"] += 280.0 * dt_sec
            engine.light_pulses = [lp for lp in engine.light_pulses if lp["dist"] < max_dist]
