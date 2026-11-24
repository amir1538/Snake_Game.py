# 🐍 Snaky Game (Native Python & pygame-ce)

**Snaky Game** is a 100% offline, native Python desktop application built with **`pygame-ce`**, faithfully recreating every feature, visual detail, animation, sound effect, and setting from the approved HTML prototype.

---

## ✨ Key Features

* **All 17 Game Modes (Real Mechanics + Blender Mode):**
  `Classic`, `Wall`, `Portal`, `Cheese`, `No Borders`, `Twin`, `Winged`, `Yin Yang`, `Key`, `Sokoban`, `Poison`, `Dimension`, `Minesweeper`, `Statue`, `Light`, `Peace`, and **`Blender`** (combine 2 or more modes simultaneously).
* **Exact Visual Recreation (Smooth & Pixel Styles):**
  * **Smooth Mode:** Quadratic Bézier curved snake body, tapered tail, elongated rounded snout, seamless eye domes with real-time eye tracking, dizzy collision eyes, straight-back collision recoil, semicircle open mouth with white fangs, swallowing apple & traveling body bulges, and periodic forked red tongue flick every 3.2 seconds.
  * **Pixel Mode:** Continuous gap-free pixel snake bar, crisp vertical pixel eyes, pixel nostrils, pixel mouth notch, blocky forked tongue flick, and 9×9 pixel-art fruits.
* **Exact Reference Main Menu & 8-Row Carousel Settings Menu:**
  * `300×366` sky-blue Main Menu card with live fruit/snake preview, 3-row checkered grass strip, and `#1155CC` **Play Snaky** & **Gear** buttons.
  * `300×366` 8-row horizontal sliding Settings carousel (Fruit, 17 Modes + Blender Mix popover, Fruit Count, Speed, Board Size, 8 Snake Color Rings, 4 Themes `Day`/`Night`/`Winter`/`Volcano`, Smooth/Pixel Graphics) + **Dice Randomizer** button + mouse-wheel support.
* **Custom `ESC` Pause & `Continue` Freeze:**
  * Pressing `ESC` immediately pauses the game and reveals the **`Continue`** button below the game area.
  * Freezes 100% of snake movement, elapsed timer, food pulse, tongue flick, swallowing bulges, eating animation, and Minesweeper countdowns with zero jumps on resume.
* **Offline Audio System:**
  * Plays the exact `assets/sound/eat_apple.wav` when eating fruit.
  * Synthesizes directional 4-pitch warm turn pops (`Up`, `Right`, `Left`, `Down`), impact+wobble death SFX, UI clicks, and mode-specific SFX completely offline.
* **True Fullscreen & Resizable Layout:** Press `F11` or click the Fullscreen icon in the top bar; the board dynamically scales to fill any resolution cleanly.
* **100% Offline Persistence:** Settings and per-configuration high scores save locally inside `data/settings.json` and `data/highscores.json`.

---

## 🚀 Installation & Offline Execution

### Prerequisites
* **Python 3.9+**
* **`pygame-ce`** (Pygame Community Edition)

### Method 1: Quick Launch (Auto-installs `pygame-ce` if missing)
```bash
python run.py
```

### Method 2: Manual Setup
```bash
pip install -r requirements.txt
python run.py
```
Once `pygame-ce` is installed, **Snaky Game** runs **100% offline** with no internet connection required.

---

## 🎮 Controls

| Key / Action | Function |
| :--- | :--- |
| **Arrow Keys** or **W, A, S, D** | Zero-latency steering (3-turn buffer, 180° reversal protection, diagonal held-key zigzagging) |
| **ESC** | **Pause / Resume** (freezes everything; shows **Continue** bar below the game area) |
| **F11** or **⛶ Button** | Toggle True Fullscreen |
| **T** | Toggle Elapsed Timer on top bar |
| **M** or **🔊 Button** | Mute / Unmute all sounds |
| **Space** or **Enter** | Start from Main Menu, Restart on Game Over/Win, or Resume when Paused |
| **⚙️ Button** | Open 8-Row Carousel Settings Menu (click or scroll mouse wheel on any row) |

---

## 🧪 Running the Automated Tests

```bash
python -m unittest discover -s tests -v
```
All 26 regression tests verify startup, settings & high-score JSON persistence, Dice randomizer, zero-latency turning, `ESC` Pause complete freeze, Board Size propagation, all 17 game modes, Sokoban regression, and audio asset/synthesis integrity.

---

## 📦 Building Standalone Windows `.exe` (`SnakyGame.exe`)

Double-click **`build_exe.bat`** on Windows, or run:

```cmd
pip install pyinstaller pygame-ce
pyinstaller --noconsole --onefile --icon="assets\icon.ico" --add-data "assets;assets" --name "SnakyGame" run.py
```

The standalone **`SnakyGame.exe`** will be generated inside `dist/` with the custom icon and `eat_apple.wav` bundled inside. At runtime, it automatically creates a `data/` folder next to `SnakyGame.exe` for persistent settings and high scores.

---

## 📂 Modular Project Structure

```text
snaky-game-python/
├── run.py                  # Entrypoint & auto-installer launcher
├── build_exe.bat           # One-click Windows PyInstaller build script
├── requirements.txt        # pygame-ce dependency
├── README.md
├── CHANGELOG.md
├── assets/
│   ├── icon.png            # Window & taskbar icon
│   ├── icon.ico            # Windows executable icon
│   └── sound/
│       └── eat_apple.wav   # Exact apple eating sound
├── data/                   # Auto-populated local JSON persistence
├── snaky/
│   ├── __init__.py
│   ├── paths.py            # Source & PyInstaller (_MEIPASS) path resolver
│   ├── constants.py        # Modes, themes, colors, fruits, speeds, board presets
│   ├── settings.py         # JSON settings & high-score persistence
│   ├── audio.py            # Offline pygame-ce audio loader & synthesizer
│   ├── modes.py            # Composable logic for all 17 modes + Blender
│   ├── engine.py           # Deterministic pause-aware simulation engine
│   ├── icons.py            # Procedural vector icons matching approved UI
│   ├── renderer.py         # Cached board, Smooth Bezier & Pixel Mode renderer
│   ├── ui.py               # Top HUD, Main Menu, 8-Row Settings Carousel, Pause Bar
│   └── app.py              # Pygame window, Fullscreen, input & 60 FPS loop
└── tests/
    └── test_snaky.py       # 26 automated regression unit tests
```
