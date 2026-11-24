# Changelog — Snaky Game

All notable changes to **Snaky Game** are documented in this file.

## [1.2.1] - 2026-11-24

### Fixes
- **Fixed Fullscreen Hang/Crash (`snaky/app.py`):** Replaced `pygame.FULLSCREEN | pygame.DOUBLEBUF` + `vsync=1` with crash-free borderless desktop fullscreen (`pygame.NOFRAME` at `0,0` with native desktop resolution), eliminating Windows SDL2 display-mode freezes on `F11` or Fullscreen button click.
- **Tight Board-Fitted Windowed Sizing (`snaky/app.py`):** Window now opens tightly fitted around the exact game board (`Small 10×9` -> `472×488`, `Regular 17×15` -> `610×602`, `Big 24×21` -> `752×722`) and automatically resizes whenever Board Size is changed in Settings while in windowed mode.

## [1.2.0] - 2026-11-24

### Fixes
- **Fixed Chopped-Up Snake & Dark Rim Artifacts (`snaky/renderer.py`):** Identified and eliminated Pygame's non-premultiplied `smoothscale` dark-halo bug (where drawing onto `(0,0,0,0)` created muddy dark rings around every stamped snake circle and turned the body into visible segments). Replaced per-circle alpha stamping with a single unified 2x supersampled snake layer pre-filled with `(*head_col, 0)` (reusing zero-copy pre-allocated scratch buffers) plus a unified flat 2x shadow layer on `(*shadow_col, 0)` and a 3x tongue layer on `(*tongue_red, 0)`. Verified via pixel scan: max adjacent body seam jump `<= 3` and `0` dark halo pixels.
- **Fixed Pixelated / Dark-Rimmed Fruits & Icons (`snaky/icons.py`, `snaky/ui.py`):** Rebuilt all fruits, obstacles, trophy, UI buttons, and all 8 Settings Carousel icon rows using multi-layer color-matched 4x SSAA (`(*layer_rgb, 0)`), and fixed rounded-corner card masks on the Main Menu and Settings cards to eliminate corner darkening.

## [1.1.0] - 2026-11-24

### Highlights
- **HD Anti-Aliased Graphics Overhaul (Zero Pixelation in Smooth Mode):** Eliminated jagged Pygame primitive edges across the entire application using 3x/2x supersampling (`pygame.transform.smoothscale`) and native Windows HiDPI awareness.

### Changes
- **Native Windows Per-Monitor HiDPI Support (`snaky/app.py`):** Enabled `SetProcessDpiAwareness(2)` / `SetProcessDPIAware()` before display creation plus VSync so Windows 10/11 renders crisp native physical pixels without blurry DWM stretching.
- **3x SSAA Smooth Snake Rendering (`snaky/renderer.py`):** Replaced jagged `pygame.draw.circle` body segments with cached 3x-supersampled anti-aliased circle stamps, added a dedicated 3x-supersampled head assembly patch (silky-smooth snout, open mouth, fangs, seamless eyes with subtle pupil catchlight, nostrils, and periodic forked tongue), and replaced banded Light Mode circles with a smoothstep 128×128 radial vignette texture.
- **3x SSAA Cached Fruits, Obstacles & UI Icons (`snaky/icons.py`, `snaky/renderer.py`):** Upgraded all 9 Smooth fruit sprites (with rich two-tone shading and specular gloss), all mode obstacles (beveled brick walls, carved stone statues, wooden crates, padlocks, golden keys, mines, rotating smooth portal rings), and all 8 Settings Carousel icon rows to 3x-supersampled cached sprites.
- **2x SSAA Main Menu Card & Anti-Aliased Buttons (`snaky/ui.py`):** Rendered the Main Menu card at `600×732` and downscaled smoothly to `300×366` (cached for 0ms per-frame overhead), and upgraded all buttons and cards with 2x anti-aliased rounded corners.

## [1.0.0] - 2026-11-24

### Highlights
- **Phase Five Complete — Native Python & `pygame-ce` Desktop Application:** Rebuilt the entire approved HTML prototype (`v0.5.1-prototype`) as a genuine, modular, 100% offline Python desktop game with zero browser/HTML runtime dependencies.
- **1:1 Gameplay, Visual & Audio Parity:** Ported all 17 game modes (including Blender composition), Smooth Bézier snake rendering (elongated snout, seamless eye domes, eye tracking, open mouth + fangs + swallowing apple/bulges, periodic forked tongue flick, straight-back collision recoil), Pixel Mode (continuous gap-free pixel snake, pixel eyes/nostrils/mouth/tongue, 9×9 pixel-art fruits), exact `assets/sound/eat_apple.wav` playback, directional 4-pitch turn pops, impact+wobble death SFX, pixel-matched `300×366` Main Menu & 8-row sliding Settings Carousel + Dice Randomizer, true Fullscreen (`F11` / HUD button), and `ESC` Pause / `Continue` bar below the board.
- **Modular Package Architecture (`rea-tool-design`):** Separated responsibilities cleanly across `snaky/paths.py`, `constants.py`, `settings.py`, `audio.py`, `modes.py`, `engine.py`, `icons.py`, `renderer.py`, `ui.py`, `app.py`, and `run.py`.
- **Verified Automated Test Suite (`rea-ci-tests-audit`):** Executed 26 native Python `unittest` regression tests (26/26 passed) plus a full mocked-Pygame render/UI/audio smoke test covering all 17 modes, both Smooth and Pixel graphics styles, pause freezing, settings persistence, and audio buffers.
- **Windows `.exe` Packaging Ready:** Included `assets/icon.ico`, `assets/icon.png`, PyInstaller `_MEIPASS` path resolution, and one-click `build_exe.bat`.

## [0.5.1-prototype] - 2026-11-24

### Changes
- **Exact Custom Apple Eating Sound (`eat_apple.wav`):** Integrated the user-supplied `eat_apple.wav` into `assets/audio/eat_apple.wav` and an offline `file://` CORS-safe Web Audio decoder (`assets/audio/eat_apple_b64.js`) so eating fruit plays the exact audio clip with zero latency.
- **Periodic Snake Tongue Flick:** Added a realistic forked red snake tongue flick every ~3.2 seconds (420ms extend/wiggle/retract) in both Smooth and Pixel modes, driven strictly by `engine.gameTimeMs` so it freezes cleanly on `ESC` Pause and hides when opening the mouth to eat.

## [0.5.0-prototype] - 2026-11-24

### Highlights
- **Exact Smooth Snake Proportions & Fullscreen-Scaled Mouth Animation:** Fixed snout length, eye placement, seamless eye domes (removed dark outline ring), forward nostrils, and removed the stray idle red tongue to match the reference game side-by-side. Scaled the Python-style semicircle open mouth, white fangs, swallowing apple, and recoil proportionally to `cellSize` so fullscreen looks identical at every resolution.
- **Exact Pixel Mode (Continuous Snake + Pixel-Art Apple):** Replaced separated square blocks with a continuous gap-free retro pixel snake bar, crisp vertical pixel eyes, pixel nostrils, pixel mouth opening, and blocky 9×9 pixel-art apple/fruit sprites.
- **Audio Upgrade (Directional Pops + Juicy Apple Crunch):** Ported the Python `generate_move_pop_samples` (`sin + tri + sub`) into pre-rendered directional Web Audio buffers (Up/Right/Left/Down distinct pitches matching `snakegame.net`), upgraded apple eating to a crisp double-bite crunch + rising pop, and ported the Python impact+wobble death SFX.

## [0.4.0-prototype] - 2026-11-24

### Highlights
- **Exact Pixel-Matched 8-Row Carousel Settings Menu:** Rebuilt the Settings Menu directly from the reference screenshot (`300×366px`, `38px` `#3A91BB` header with white back arrow, 8 horizontal `41px` `#4DC1F9` carousel rows with `1px #87CEFA` dividers, active icon centered at `x=150px` at 100% opacity, inactive icons at 42% opacity spaced `40px` apart with smooth horizontal slide & mouse-wheel scrolling, and bottom `224×64px` Play Snaky + `64×64px` `#1155CC` Dice Randomizer button).
- **Exact 8 Settings Rows Verified from Reference Screenshot:**
  1. Fruit (`Apple`, `Banana`, `Pineapple`, `Grapes`, `Cherry`, `Watermelon`, `Strawberry`, `Orange`, `Random`)
  2. Game Mode (all 17 modes starting with Gold Trophy Classic, Brick Wall, Portal Snake, Swiss Cheese, + Blender Mix popover)
  3. Fruit Count (`1`, `3`, `5`, `Dice`)
  4. Speed (`Normal` S-snake, `Fast` rabbit, `Slow` turtle)
  5. Board Size (`Regular`, `Small`, `Big` scaled checkered squares)
  6. Snake Color (curled snake-ring icons in `Blue`, `Cyan`, `Purple`, `Pink`, `Red`, `Orange`, `Yellow`, `Green`)
  7. Theme (`Day` sun, `Night` moon, `Winter` snowflake, `Volcano`)
  8. Graphics Style (`Smooth` round eyes vs `Pixel` retro blocky eyes, with live pixel-mode rendering in `renderer.js`).

## [0.3.0-prototype] - 2026-11-22

### Highlights
- **Pixel-Matched Main Menu Recreation:** Rebuilt the Main Menu card (`300×366px`, `8px` radius, `#4DC1F9` sky, `77px` 3-row `26×26px` checkered `#A6D948`/`#8ECC3A` grass, pixel-faithful inline SVG smiling snake, centered Apple & Trophy score columns) and bottom action bar (`12px` gap, `224×64px` `#1155CC` **Play Snaky** button + `12px` gap + `64×64px` `#1155CC` outlined Gear button) directly from pixel measurements of the reference screenshot.
- **Reference-Style Icon-First Settings Menu Recreation:** Replaced the text-pill settings modal with a compact sky-blue (`#4DC1F9`) sibling card (`368px` wide) featuring a `#4A752C` top bar (Back, Timer, Mute, Reset icon buttons), 100% custom inline SVG icon selectors for all 17 modes (with carousel arrows and inline Blender multi-icon mix tray), Fruit Type, Fruit Count, Speed, Board Size, 7 classic solid Snake Colors, and Day/Night Theme, plus a matching `64px` `#1155CC` **Play Snaky** button underneath.

### Changes
- **Zero OS Emojis in Menus:** Replaced all raw system emoji icons in the Main Menu and Settings Menu with crisp, custom offline inline SVGs.
- **Live Main Menu Preview Sync:** Selecting a Fruit Type, Snake Color, or Day/Night Theme in Settings dynamically updates the Main Menu card's fruit icon, smiling snake color, sky, and grass strip.
- **Zero Unnecessary Customization Confirmed:** Retained only the 7 classic solid snake colors and Day/Night themes (no RGB pickers, no gradients, no extra custom themes).

### Fixes
- **Renderer Crash Fix (`js/renderer.js`):** Fixed a 1-line accidental self-recursion typo in `drawRoundRect()` (`drawRoundRect(...)` -> `ctx.roundRect(...)`) so selecting Statue, Key, or Sokoban mode from the Settings Menu renders without throwing a stack overflow error.
- **Preserved Gameplay Scope:** Left `js/engine.js`, `js/modes.js`, `js/audio.js`, `js/constants.js`, `js/settings.js`, `js/main.js`, and `tests/test_suite.js` untouched.

## [0.2.0-prototype] - 2026-11-22

### Highlights
- **Reference-Faithful UI & Main Menu:** Rebuilt the Main Menu, Game Over card, top HUD bar, and Settings modal to match the original reference style (sky-blue card with vector Apple/Trophy and smiling snake on grass, royal-blue Play & Gear buttons, classic green top bar with inline SVG icons).
- **True Fullscreen Layout + Fullscreen API:** Removed outer dark margins, borders, and small centered webpage frame; the game now occupies 100vw × 100vh with dynamic viewport-fitted tile scaling and a browser Fullscreen toggle button.
- **Immediate Keyboard Input (Zero Artificial Delay):** Eliminated LEFT/RIGHT/UP/DOWN input lag by executing the initial move immediately on `keydown`, expanding turn buffering to 3 rapid inputs, gating diagonal held-key polling until after a step executes, and removing 60 FPS DOM thrashing.
- **Settings Root-Cause Fix:** Changing Board Size, Mode, Speed, Fruit Count, or Fruit Type now immediately propagates to the running engine and recalculates board dimensions, rendering cache, food bounds, and collision bounds.

### Changes
- **Removed Unnecessary Customization:** Removed invented custom themes (`Desert`, `Oceanic`, `Volcano`, `Monochrome`) and non-reference gradient/rainbow snake options (`Sunset Gradient`, `Rainbow`), restoring classic solid colors and Day/Night themes.
- **Startup Flow:** Added explicit `MENU` state on launch matching the reference Main Menu card.
- **Performance (`rea-analysis-optimization`):** Implemented dirty-checked HUD synchronization in `UIController.syncHud()` so the DOM is only touched when values actually change.
- **Regression Tests (`rea-ci-tests-audit`):** Added automated regression tests for Board Size propagation, zero-latency LEFT/RIGHT input buffering, Sokoban non-scoring crate pushes, and reference color/theme cleanup (27 total tests).

### Fixes
- **Settings Desync Bug:** Fixed closing Settings via `✕` or `ESC` leaving the engine with stale `cols`, `rows`, `speed`, or `activeModes`.
- **Sokoban False Growth Bug:** Fixed pushing a crate onto a non-target cell immediately after eating food erroneously growing the snake by checking an explicit `scoredCrate` flag.
- **Browser Compatibility:** Added safe `drawRoundRect()` fallback in `renderer.js` for browsers without `CanvasRenderingContext2D.roundRect`.

## [0.1.0-prototype] - 2026-11-22

### Highlights
- Completed Phase One reverse-engineering inventory of all 17 documented game modes and settings.
- Completed Phase Two audit of the existing Python project (`Snake_game_offline.py`).
- Built the initial modular, 100% offline **Snaky Game** HTML5 prototype with all 17 modes, Blender Mode, curved Bézier snake rendering, Web Audio SFX, and pause-aware `gameTimeMs` animation freezing.
