# 🐍 Modern Snake Game (Python & Pygame)

Welcome to my very first GitHub repository! 🎉  
Hi, I'm **amir1538**, and this project is a modern, smooth, and offline **Snake Game** built with Python.

To be completely honest, I am still new to programming and don't have much coding experience yet—I built this game with the help of AI as a fun learning journey to understand how game development works in Python. 

If you enjoy playing it or find the code useful, **please consider giving this repository a Star ⭐!** Your support means the world to me and motivates me to keep learning and building better projects in the future.

---

## ✨ Features

* **Smooth Curved Movement:** Unlike traditional blocky snake games, the snake's body uses quadratic Bézier curves to bend and slither smoothly around corners.
* **Expressive Animations:** 
  * Dynamic eyes that track the apple in real-time.
  * Smooth mouth-opening animation when approaching food and a visible swallowing bulge moving down the body.
  * Straight-back recoil and dizzy eye animations upon collision.
* **Custom Audio System:** 
  * Crisp apple crunch sound effect (`eat_apple.wav`).
  * Randomized directional pop sounds (`move_1.wav` to `move_4.wav`) that never repeat the same pitch twice in a row.
  * Instant Mute/Unmute toggle button in the top bar (or press `M`).
* **Pause & Continue Menu:** Press `ESC` at any time during the game to pause and resume seamlessly via the interactive card menu.
* **Persistent High Score:** Automatically saves your best record locally in `data/highscore.json` so your progress is never lost.
* **Standalone Executable Ready:** Fully compatible with `PyInstaller` to run as a standalone Windows `.exe` file without needing Python installed.

---

## 🛠️ Built With (Libraries Used)

This project relies on Python's built-in standard libraries alongside **Pygame Community Edition**:

* **[Python 3.8+](https://www.python.org/)**
* **[pygame-ce](https://pypi.org/project/pygame-ce/)** (Pygame Community Edition) – Used for 2D hardware-accelerated rendering, window management, event handling, and low-latency audio mixing.
* **Python Standard Libraries:** `os`, `sys`, `math`, `random`, `json`, `wave`, `struct`, `io`, `ctypes` (built into Python; no extra installation required).

---

## 🚀 How to Install & Run

You can run the game either directly from the Python source code or via the standalone `.exe` file (if downloaded from the Releases section).

### Method 1: Quick Start using `run.py` (Recommended)
The included `run.py` launcher automatically checks if `pygame-ce` is installed, installs it if missing, and launches the game:

```bash
git clone https://github.com/amir1538/Snake_Game.git
cd Snake_Game
python run.py
```

### Method 2: Manual Installation
1. Make sure you have **Python 3.8+** installed on your system.
2. Install the required library via terminal / CMD:
   ```bash
   pip install pygame-ce
   ```
3. Run the main game script:
   ```bash
   python Snake_game_offline.py
   ```

---

## 🎮 Controls

| Key / Action | Function |
| :--- | :--- |
| **Arrow Keys** or **W, A, S, D** | Move the Snake (Hold two adjacent keys for smooth diagonal zigzagging) |
| **ESC** | Pause / Resume the game (`Continue` menu) |
| **SPACE** or **ENTER** | Start a new game (on Game Over) or Resume (when Paused) |
| **M** or **Speaker Icon** | Mute / Unmute all game sounds |

---

## 📂 Project Structure

```text
Snake_Game/
├── Snake_game_offline.py    # Main game source code
├── run.py                   # Auto-installer and game launcher script
├── icon.png                 # Window & taskbar icon
├── icon.ico                 # Executable icon for Windows
├── README.md                # Project documentation
├── sound/                   # Audio assets folder
│   ├── eat_apple.wav
│   ├── move_1.wav
│   ├── move_2.wav
│   ├── move_3.wav
│   └── move_4.wav
└── data/                    # Auto-generated folder for saving high scores
    └── highscore.json
```

---

## 📦 Building the `.exe` File Yourself

If you want to compile the game into a single standalone `.exe` file on Windows, run the following commands in the project folder:

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --icon="icon.ico" --add-data "sound;sound" --add-data "icon.png;." --name "SnakeGame" Snake_game_offline.py
```
The final `SnakeGame.exe` file will appear inside the `dist/` folder.

---

## 🤝 Contributing & Feedback

Since this is my first project and I am still learning the ropes, the code is completely open for everyone!  
If you want to use this project, fix a bug, or add new features (like a settings menu, new game modes, or different snake colors), feel free to:
* Open an **Issue** or submit a **Pull Request**.
* Contact me (**[@amir1538](https://github.com/amir1538)**) if you've improved the game—I would love to check out your changes and publish the updates here!

---

## 👤 Author

* **amir1538** - [GitHub Profile](https://github.com/amir1538)

**Don't forget to leave a ⭐ if you liked this project! Thank you for visiting!** ❤️
