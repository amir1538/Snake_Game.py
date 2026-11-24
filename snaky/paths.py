"""Path resolution compatible with both standard Python execution and PyInstaller .exe bundles."""

import os
import sys


def get_base_dir() -> str:
    """Writable directory next to the executable (or project root in source mode)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # snaky/paths.py -> parent of snaky/
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
    """Return (and ensure creation of) the persistent local data/ directory."""
    d = os.path.join(get_base_dir(), "data")
    os.makedirs(d, exist_ok=True)
    return d
