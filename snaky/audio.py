"""Snaky Game — Offline Audio Manager (pygame-ce mixer).

- Loads the exact user-provided `assets/sound/eat_apple.wav` directly.
- Synthesizes directional 4-pitch warm turn pops (Up/Right/Left/Down, sin+tri+sub),
  impact+wobble death SFX, click SFX, and mode SFX (portal, key unlock, crate push,
  poison, dimension shift, win) in memory with zero external dependencies.
"""

import io
import math
import os
import random
import struct
import wave
from typing import Optional

from .paths import get_asset_path, get_base_dir


class NullAudioManager:
    """No-op audio manager for headless automated unit tests."""

    def __init__(self, muted: bool = True) -> None:
        self.muted = muted

    def set_muted(self, muted: bool) -> None:
        self.muted = bool(muted)

    def play_turn(self, dx: int = 0, dy: int = 0) -> None:
        pass

    def play_eat(self) -> None:
        pass

    def play_die(self) -> None:
        pass

    def play_click(self) -> None:
        pass

    def play_portal(self) -> None:
        pass

    def play_key_unlock(self) -> None:
        pass

    def play_crate_push(self) -> None:
        pass

    def play_poison(self) -> None:
        pass

    def play_dimension_shift(self) -> None:
        pass

    def play_win(self) -> None:
        pass


def _samples_to_wav_bytes(samples, sample_rate: int = 22050) -> io.BytesIO:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        packed = struct.pack(f"<{len(samples)}h", *samples)
        wf.writeframesraw(packed)
    buf.seek(0)
    return buf


def _make_move_pop_samples(f_start: float, f_end: float, dur: float, sr: int = 22050):
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
        val = (0.76 * sin_w + 0.16 * tri_w + 0.08 * sub_w) * env * 0.68
        samples.append(max(-32767, min(32767, int(val * 32767))))
    return samples


def _make_die_samples(sr: int = 22050):
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
            val = (math.sin(2.0 * math.pi * phase) + impact_noise) * env * 0.78
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
            val = (0.50 * sin_w + 0.35 * saw + 0.15 * sq) * env * 0.68
        samples.append(max(-32767, min(32767, int(val * 32767))))
    return samples


def _make_click_samples(sr: int = 22050):
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
        val = math.sin(2.0 * math.pi * phase) * env * 0.42
        samples.append(max(-32767, min(32767, int(val * 32767))))
    return samples


def _make_sweep_samples(f1: float, f2: float, dur: float, wave_type: str = "sine", vol: float = 0.28, sr: int = 22050):
    n = int(sr * dur)
    samples = []
    phase = 0.0
    for i in range(n):
        t = i / sr
        p = t / dur
        freq = f1 * ((f2 / f1) ** p) if f1 > 0 and f2 > 0 else f1
        phase += freq / sr
        env = min(1.0, t / 0.004) * math.exp(-p * 4.5)
        if wave_type == "square":
            raw = 1.0 if math.sin(2.0 * math.pi * phase) >= 0 else -1.0
        elif wave_type == "saw":
            raw = 2.0 * (phase - math.floor(phase + 0.5))
        elif wave_type == "tri":
            raw = 2.0 * abs(2.0 * (phase - math.floor(phase + 0.5))) - 1.0
        else:
            raw = math.sin(2.0 * math.pi * phase)
        val = raw * env * vol
        samples.append(max(-32767, min(32767, int(val * 32767))))
    return samples


def _make_arpeggio_samples(freqs, step_s: float, note_dur: float, vol: float = 0.28, sr: int = 22050):
    total_dur = (len(freqs) - 1) * step_s + note_dur
    n = int(sr * total_dur)
    buf = [0.0] * n
    for idx, freq in enumerate(freqs):
        start_i = int(idx * step_s * sr)
        note_n = int(note_dur * sr)
        phase = 0.0
        for j in range(note_n):
            pos = start_i + j
            if pos >= n:
                break
            p = j / max(1, note_n)
            phase += freq / sr
            env = min(1.0, (j / sr) / 0.004) * math.exp(-p * 4.2)
            tri = 2.0 * abs(2.0 * (phase - math.floor(phase + 0.5))) - 1.0
            buf[pos] += tri * env * vol
    return [max(-32767, min(32767, int(v * 32767))) for v in buf]


class AudioManager:
    """Offline pygame-ce sound manager matching the approved HTML prototype audio."""

    def __init__(self, muted: bool = False) -> None:
        import pygame

        self._pygame = pygame
        self.muted = bool(muted)
        self.ready = False
        self.last_turn_key = ""
        self.sounds = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 512)
            pygame.mixer.set_num_channels(16)
            self.ready = True
        except Exception:
            self.ready = False
            return

        self._load_all_sounds()

    def _sound_from_samples(self, samples, volume: float = 0.9):
        wav_io = _samples_to_wav_bytes(samples)
        s = self._pygame.mixer.Sound(file=wav_io)
        s.set_volume(volume)
        return s

    def _load_all_sounds(self) -> None:
        pygame = self._pygame

        # 1. Exact eat_apple.wav (check assets/sound/eat_apple.wav, sound/eat_apple.wav, root)
        eat_candidates = [
            get_asset_path("sound", "eat_apple.wav"),
            os.path.join(get_base_dir(), "sound", "eat_apple.wav"),
            os.path.join(get_base_dir(), "eat_apple.wav"),
        ]
        eat_sound = None
        for path in eat_candidates:
            if os.path.isfile(path):
                try:
                    eat_sound = pygame.mixer.Sound(path)
                    eat_sound.set_volume(1.0)
                    break
                except Exception:
                    pass
        if eat_sound is None:
            eat_sound = self._sound_from_samples(_make_sweep_samples(440.0, 780.0, 0.14, "tri", 0.55), 0.9)
        self.sounds["eat"] = eat_sound

        # 2. Directional 4-pitch warm turn pops (Up, Right, Left, Down)
        # If user placed custom move_1..4.wav inside assets/sound or sound/, support them or use synthesized pops
        self.sounds["turn_up"] = self._sound_from_samples(_make_move_pop_samples(262.0, 215.0, 0.060), 0.92)
        self.sounds["turn_right"] = self._sound_from_samples(_make_move_pop_samples(228.0, 185.0, 0.062), 0.92)
        self.sounds["turn_left"] = self._sound_from_samples(_make_move_pop_samples(198.0, 152.0, 0.064), 0.92)
        self.sounds["turn_down"] = self._sound_from_samples(_make_move_pop_samples(168.0, 125.0, 0.068), 0.92)

        # 3. Core SFX loaded upfront; rare mode SFX synthesized lazily on first use for instant startup
        self.sounds["die"] = self._sound_from_samples(_make_die_samples(), 0.95)
        self.sounds["click"] = self._sound_from_samples(_make_click_samples(), 0.75)
        self._lazy_factories = {
            "portal": lambda: self._sound_from_samples(_make_sweep_samples(280.0, 920.0, 0.16, "sine", 0.35), 0.9),
            "key_unlock": lambda: self._sound_from_samples(_make_arpeggio_samples([523.25, 659.25, 783.99], 0.045, 0.13, 0.32), 0.9),
            "crate_push": lambda: self._sound_from_samples(_make_sweep_samples(110.0, 75.0, 0.08, "square", 0.22), 0.85),
            "poison": lambda: self._sound_from_samples(_make_sweep_samples(340.0, 150.0, 0.24, "saw", 0.30), 0.9),
            "dimension": lambda: self._sound_from_samples(_make_sweep_samples(620.0, 310.0, 0.14, "sine", 0.30), 0.9),
            "win": lambda: self._sound_from_samples(_make_arpeggio_samples([523.25, 659.25, 783.99, 1046.5], 0.08, 0.23, 0.34), 0.95),
        }

    def set_muted(self, muted: bool) -> None:
        self.muted = bool(muted)
        if self.muted and self.ready:
            try:
                self._pygame.mixer.stop()
            except Exception:
                pass

    def _play(self, key: str) -> None:
        if self.muted or not self.ready:
            return
        snd = self.sounds.get(key)
        if snd is None and hasattr(self, "_lazy_factories") and key in self._lazy_factories:
            try:
                snd = self._lazy_factories.pop(key)()
                self.sounds[key] = snd
            except Exception:
                snd = None
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def play_turn(self, dx: int = 0, dy: int = 0) -> None:
        if dy == -1:
            key = "turn_up"
        elif dy == 1:
            key = "turn_down"
        elif dx == -1:
            key = "turn_left"
        elif dx == 1:
            key = "turn_right"
        else:
            choices = [k for k in ("turn_down", "turn_left", "turn_right", "turn_up") if k != self.last_turn_key]
            key = random.choice(choices)
        self.last_turn_key = key
        self._play(key)

    def play_eat(self) -> None:
        self._play("eat")

    def play_die(self) -> None:
        self._play("die")

    def play_click(self) -> None:
        self._play("click")

    def play_portal(self) -> None:
        self._play("portal")

    def play_key_unlock(self) -> None:
        self._play("key_unlock")

    def play_crate_push(self) -> None:
        self._play("crate_push")

    def play_poison(self) -> None:
        self._play("poison")

    def play_dimension_shift(self) -> None:
        self._play("dimension")

    def play_win(self) -> None:
        self._play("win")
