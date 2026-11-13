import os
import subprocess
import sys


def ensure_pygame_installed():
    """بررسی نصب بودن pygame و نصب خودکار در صورت نیاز"""
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("[*] Installing pygame-ce...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pygame-ce"]
        )


def start_game():
    """تنظیم مسیر پوشه پروژه و اجرای بازی اصلی"""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    ensure_pygame_installed()

    import Snake_game_offline

    Snake_game_offline.main()


if __name__ == "__main__":
    start_game()