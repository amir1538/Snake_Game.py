"""Snaky Game — Main Entrypoint & Auto-Launcher."""

import os
import subprocess
import sys


def ensure_pygame_installed() -> None:
    """Install pygame-ce automatically if running from source without it."""
    if getattr(sys, "frozen", False):
        return
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("[Snaky Game] pygame-ce not found. Installing pygame-ce...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce"])


def main() -> None:
    if not getattr(sys, "frozen", False):
        project_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(project_dir)
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)
        ensure_pygame_installed()

    from snaky.app import main as launch_app

    launch_app()


if __name__ == "__main__":
    main()
