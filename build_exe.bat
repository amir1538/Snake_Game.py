@echo off
echo [Snaky Game] Building standalone Windows executable (SnakyGame.exe)...
pip install pyinstaller pygame-ce
pyinstaller --noconsole --onefile --icon="assets\icon.ico" --add-data "assets;assets" --name "SnakyGame" run.py
echo.
echo Done! Find your standalone executable at: dist\SnakyGame.exe
pause
