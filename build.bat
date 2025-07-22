@echo off
echo building...
echo.
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec

python -m PyInstaller ^
    --onefile ^
    --icon=assets/icon.ico ^
    --name=BubbaversePlayerLauncher ^
    --add-data="assets;assets" ^
    --add-data="version_info.txt;." ^
    --optimize=2 ^
    --strip ^
    --noupx ^
    --console ^
    --version-file=version_info.txt ^
    main.py

:: verify build
if exist "dist\BubbaversePlayerLauncher.exe" (
    echo Build successful!
    echo.
    echo Executable: dist\BubbaversePlayerLauncher.exe
) else (
    echo Build failed!
)

echo.
pause