@echo off
echo [Snaky Game] Building standalone Windows executable (SnakyGame.exe)...
python -m pip install --upgrade pyinstaller pygame-ce
python -m PyInstaller --noconsole --onefile --clean --icon="assets\icon.ico" --add-data "assets;assets" --collect-all snaky --name "SnakyGame" run.pyecho.
echo Done! Find your standalone executable at: dist\SnakyGame.exe
pause
