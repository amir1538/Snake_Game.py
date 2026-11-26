"""Path resolution compatible with both standard Python execution and PyInstaller .exe bundles.

Persistent user data (settings.json, highscores.json) is stored in:
- Windows: %LOCALAPPDATA%\Snaky Game  (AppData\Local\Snaky Game)
- macOS:   ~/Library/Application Support/Snaky Game
- Linux:   ~/.local/share/Snaky Game
"""

import os
import shutil
import sys


def get_base_dir() -> str:
    """Directory next to the executable (or project root in source mode)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_dir() -> str:
    """Read-only asset bundle directory (_MEIPASS when frozen, project root otherwise)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return get_base_dir()


def get_asset_path(*parts: str) -> str:
    """Resolve an asset inside assets/, falling back to base_dir if unpacked externally."""
    cand = os.path.join(get_resource_dir(), "assets", *parts)
    if os.path.exists(cand):
        return cand
    return os.path.join(get_base_dir(), "assets", *parts)


def get_data_dir() -> str:
    """Return (and ensure creation of) the persistent user data directory in AppData\\Local\\Snaky Game."""
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA")
        if not local_app:
            local_app = os.path.join(os.path.expanduser("~"), "AppData", "Local")
        data_dir = os.path.join(local_app, "Snaky Game")
    elif sys.platform == "darwin":
        data_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Snaky Game")
    else:
        xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
        data_dir = os.path.join(xdg, "Snaky Game")

    os.makedirs(data_dir, exist_ok=True)

    # One-time seamless migration if user had an older local ./data/ folder next to the game
    legacy_dir = os.path.join(get_base_dir(), "data")
    if os.path.isdir(legacy_dir) and os.path.abspath(legacy_dir) != os.path.abspath(data_dir):
        for fname in ("settings.json", "highscores.json", "highscore.json"):
            src = os.path.join(legacy_dir, fname)
            dst = os.path.join(data_dir, fname)
            if os.path.isfile(src) and not os.path.isfile(dst):
                try:
                    shutil.copy2(src, dst)
                except Exception:
                    pass

    return data_dir
