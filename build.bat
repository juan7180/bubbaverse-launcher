@echo off
setlocal enabledelayedexpansion

echo building...
echo.

if exist "version" del /q version
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec

set "chars=abcdefghijklmnopqrstuvwxyz0123456789"
set "version="
for /L %%i in (1,1,16) do (
    set /a "rand=!random! %% 36"
    for %%c in (!rand!) do set "version=!version!!chars:~%%c,1!"
)

echo version-%version% > version
echo Generated version: version-%version%

for %%f in (*2021client.zip) do (
    ren "%%f" "version-%version%-2021client.zip"
    echo Renamed "%%f" to "version-%version%-2021client.zip"
)

python -m PyInstaller ^
    --onefile ^
    --icon=assets/icon.ico ^
    --name=BubbaversePlayerLauncher ^
    --add-data="assets;assets" ^
    --add-data="version;." ^
    --add-data="version_info.txt;." ^
    --optimize=2 ^
    --strip ^
    --noupx ^
    --console ^
    --version-file=version_info.txt ^
    main.py

:: verify build and create versioned copy
if exist "dist\BubbaversePlayerLauncher.exe" (
    copy "dist\BubbaversePlayerLauncher.exe" "dist\version-%version%-BubbaversePlayerLauncher.exe"
    echo Build successful!
    echo.
    echo Standard executable: dist\BubbaversePlayerLauncher.exe
    echo Versioned executable: dist\version-%version%-BubbaversePlayerLauncher.exe
) else (
    echo Build failed!
)

echo.
pause