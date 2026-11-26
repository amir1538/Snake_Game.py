"""Snaky Game — Native HiDPI Desktop Application (pygame-ce).

- Windowed Mode: Window tightly fits the exact game board (Small / Regular / Big)
  and automatically resizes once when Board Size is changed in Settings.
- Fullscreen Mode (F11 or HUD button): Crash-free borderless fullscreen at exact (0, 0)
  occupying 100% of the monitor without SDL2 hangs, downward offsets, or resize loops.
"""

import ctypes
import os
import sys
from typing import Tuple

import pygame

from . import constants as C
from .audio import AudioManager
from .engine import GameEngine
from .paths import get_asset_path
from .renderer import BoardRenderer
from .settings import SettingsManager
from .ui import UIController


KEY_TO_DIR = {
    pygame.K_UP: (0, -1, "UP"),
    pygame.K_w: (0, -1, "UP"),
    pygame.K_DOWN: (0, 1, "DOWN"),
    pygame.K_s: (0, 1, "DOWN"),
    pygame.K_LEFT: (-1, 0, "LEFT"),
    pygame.K_a: (-1, 0, "LEFT"),
    pygame.K_RIGHT: (1, 0, "RIGHT"),
    pygame.K_d: (1, 0, "RIGHT"),
}

# Ideal windowed cell size per Board Size so Small < Regular < Big visibly resizes the window
WINDOWED_CELL_BY_BOARD = {
    "small": 44,    # 10x9  -> board 440x396 -> window ~472x488
    "regular": 34,  # 17x15 -> board 578x510 -> window ~610x602
    "big": 30,      # 24x21 -> board 720x630 -> window ~752x722
}


def _enable_hidpi_windows() -> None:
    """Enable native Per-Monitor HiDPI rendering on Windows 10/11."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("amir1538.snakygame.desktop.1")
    except Exception:
        pass


def _detect_desktop_size() -> Tuple[int, int]:
    """Returns true primary monitor resolution using pygame-ce desktop API with safe fallback."""
    try:
        sizes = pygame.display.get_desktop_sizes()
        if sizes and sizes[0][0] > 0 and sizes[0][1] > 0:
            return (int(sizes[0][0]), int(sizes[0][1]))
    except Exception:
        pass
    try:
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return (int(info.current_w), int(info.current_h))
    except Exception:
        pass
    return (1920, 1080)


class SnakyApp:
    """Main desktop application controller."""

    def __init__(self) -> None:
        _enable_hidpi_windows()

        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()

        self.desktop_size: Tuple[int, int] = _detect_desktop_size()

        self.settings_manager = SettingsManager()
        self.audio = AudioManager(muted=self.settings_manager.get()["muted"])
        self.engine = GameEngine(self.settings_manager, self.audio)
        self.renderer = BoardRenderer()

        self.is_fullscreen = False
        self._last_board_dims = (self.engine.cols, self.engine.rows)
        self.windowed_size = self._compute_tight_window_size()

        # Center the initial window cleanly via SDL2 env before the first set_mode
        os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        pygame.display.set_caption(C.PRODUCT_NAME)

        icon_path = get_asset_path("icon.png")
        if os.path.isfile(icon_path):
            try:
                pygame.display.set_icon(pygame.image.load(icon_path))
            except Exception:
                pass

        self.ui = UIController(self.engine, self.settings_manager, self.audio, self.renderer)
        self.ui.update_layout(*self.screen.get_size())
        self.clock = pygame.time.Clock()
        self.running = True

    def _compute_tight_window_size(self) -> Tuple[int, int]:
        """Calculates the exact compact window dimensions tightly wrapping the current board."""
        board_id = self.settings_manager.get()["board_size"]
        base_cell = WINDOWED_CELL_BY_BOARD.get(board_id, 34)

        max_w = max(480, int(self.desktop_size[0] * 0.88))
        max_h = max(460, int(self.desktop_size[1] * 0.86))

        pad2 = UIController.BOARD_PAD * 2
        extra_h = UIController.TOP_BAR_H + pad2

        max_cell_w = (max_w - pad2) // max(1, self.engine.cols)
        max_cell_h = (max_h - extra_h) // max(1, self.engine.rows)
        cell = max(18, min(base_cell, max_cell_w, max_cell_h))

        win_w = max(360, self.engine.cols * cell + pad2)
        win_h = max(480, self.engine.rows * cell + extra_h)
        return (win_w, win_h)

    @staticmethod
    def _clear_stale_resize_events() -> None:
        """Flushes synthetic SDL2 resize events queued during a programmatic mode/size switch."""
        ev_types = [pygame.VIDEORESIZE]
        for name in ("WINDOWRESIZED", "WINDOWSIZECHANGED"):
            ev_id = getattr(pygame, name, None)
            if ev_id is not None:
                ev_types.append(ev_id)
        try:
            pygame.event.clear(ev_types)
        except Exception:
            pass

    @staticmethod
    def _move_window_only(x: int, y: int) -> None:
        """Moves the existing window to (x, y) WITHOUT ever altering its width/height (SWP_NOSIZE)."""
        try:
            from pygame._sdl2.video import Window

            win = Window.from_display_module()
            win.position = (int(x), int(y))
            return
        except Exception:
            pass

        if sys.platform == "win32":
            try:
                hwnd = pygame.display.get_wm_info().get("window")
                if hwnd:
                    # SWP_NOSIZE (0x0001) | SWP_NOZORDER (0x0004) | SWP_NOACTIVATE (0x0010) = 0x0015
                    ctypes.windll.user32.SetWindowPos(hwnd, 0, int(x), int(y), 0, 0, 0x0015)
            except Exception:
                pass

    def _apply_windowed_mode(self, size: Tuple[int, int]) -> None:
        """Applies windowed RESIZABLE display mode and centers window without altering size."""
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        cx = max(0, (self.desktop_size[0] - size[0]) // 2)
        cy = max(32, (self.desktop_size[1] - size[1]) // 2)
        self._move_window_only(cx, cy)
        self._clear_stale_resize_events()

    def _apply_fullscreen_mode(self) -> None:
        """Applies crash-free borderless fullscreen snapped cleanly to top-left (0, 0)."""
        dw, dh = self.desktop_size
        self.screen = pygame.display.set_mode((dw, dh), pygame.NOFRAME)
        self._move_window_only(0, 0)
        self._clear_stale_resize_events()

    def _sync_window_to_board_size(self) -> None:
        """If Board Size changed while in windowed mode, resize the window tightly to match."""
        dims = (self.engine.cols, self.engine.rows)
        if dims == self._last_board_dims:
            return
        self._last_board_dims = dims
        self.windowed_size = self._compute_tight_window_size()
        if not self.is_fullscreen:
            self._apply_windowed_mode(self.windowed_size)
        self.renderer.invalidate_cache()
        self.ui.update_layout(*self.screen.get_size())

    def toggle_fullscreen(self) -> None:
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self._apply_fullscreen_mode()
        else:
            self.windowed_size = self._compute_tight_window_size()
            self._apply_windowed_mode(self.windowed_size)
        self.ui.is_fullscreen = self.is_fullscreen
        self.renderer.invalidate_cache()
        self.ui.update_layout(*self.screen.get_size())

    def _handle_key_down(self, key: int) -> None:
        if key == pygame.K_F11:
            self.audio.play_click()
            self.toggle_fullscreen()
            return

        if key == pygame.K_ESCAPE and self.ui.is_settings_open:
            self.ui.close_settings(start_playing=False)
            return
        if self.ui.is_settings_open:
            return

        if key in KEY_TO_DIR:
            dx, dy, tag = KEY_TO_DIR[key]
            self.engine.held_dirs.add(tag)
            self.engine.queue_direction(dx, dy)
            return

        if key == pygame.K_ESCAPE:
            self.engine.toggle_pause()
            self.ui.update_layout(*self.screen.get_size())
            return

        if key == pygame.K_m:
            next_muted = not self.settings_manager.get()["muted"]
            self.settings_manager.update(muted=next_muted)
            self.audio.set_muted(next_muted)
            if not next_muted:
                self.audio.play_click()
            return

        if key == pygame.K_t:
            next_timer = not self.settings_manager.get()["show_timer"]
            self.settings_manager.update(show_timer=next_timer)
            self.audio.play_click()
            return

        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if self.engine.state == "MENU":
                self.audio.play_click()
                self.engine.start_from_menu()
            elif self.engine.state in ("GAMEOVER", "WON"):
                self.audio.play_click()
                self.engine.reset(show_menu=False)
            elif self.engine.state == "PAUSED":
                self.engine.resume()
                self.ui.update_layout(*self.screen.get_size())

    def _handle_key_up(self, key: int) -> None:
        if key in KEY_TO_DIR:
            _, _, tag = KEY_TO_DIR[key]
            self.engine.held_dirs.discard(tag)

    def _handle_video_resize(self, w: int, h: int) -> None:
        """Handles user-driven window resize safely WITHOUT calling set_mode() (prevents SDL2 loops)."""
        if self.is_fullscreen:
            return
        surf = pygame.display.get_surface()
        if surf is not None:
            self.screen = surf
            self.windowed_size = surf.get_size()
        else:
            self.windowed_size = (max(360, int(w)), max(460, int(h)))
        self.ui.update_layout(*self.screen.get_size())

    def run(self) -> None:
        while self.running:
            dt_ms = float(self.clock.tick(60))
            dt_sec = min(0.05, dt_ms / 1000.0)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.settings_manager.record_score(self.engine.score, immediate=True)
                    self.settings_manager.flush()
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self._handle_video_resize(event.w, event.h)
                elif event.type == pygame.KEYDOWN:
                    self._handle_key_down(event.key)
                elif event.type == pygame.KEYUP:
                    self._handle_key_up(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.ui.handle_mouse_down(event.pos, event.button, self.toggle_fullscreen)
                    self._sync_window_to_board_size()
                    self.ui.update_layout(*self.screen.get_size())
                elif event.type == pygame.MOUSEWHEEL:
                    self.ui.handle_mouse_wheel(pygame.mouse.get_pos(), event.y)
                    self._sync_window_to_board_size()

            self.engine.update(dt_ms)
            self.ui.update_layout(*self.screen.get_size())
            board_surf = self.renderer.render(self.engine)
            self.ui.render(self.screen, board_surf, pygame.mouse.get_pos(), dt_sec)
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)


def main() -> None:
    app = SnakyApp()
    app.run()
