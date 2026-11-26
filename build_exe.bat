@echo off
cd /d "%~dp0"
echo [Snaky Game] Building standalone Windows executable (SnakyGame.exe)...
python -m pip install --upgrade pyinstaller pygame-ce
rmdir /s /q build dist 2>nul
python -m PyInstaller --noconsole --onefile --clean --icon="assets\icon.ico" --add-data "assets;assets" --collect-all snaky --name "SnakyGame" run.py
echo.
echo Done! Find your standalone executable at: dist\SnakyGame.exe
pause
