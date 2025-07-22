@echo off
echo building..
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --icon=assets/icon.ico ^
    --name=BubbaversePlayerLauncher ^
    --add-data="assets;assets" ^
    --optimize=2 ^
    --strip ^
    --noupx ^
    --console ^
    --version-file=version_info.txt ^
    launcher.py

echo complete
pause