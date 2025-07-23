#!/usr/bin/env bash
set -e

rm -f version
rm -rf dist build
rm -f *.spec

CHARS=abcdefghijklmnopqrstuvwxyz0123456789
VERSION=""
for i in {1..16}; do
    RAND=$((RANDOM % 36))
    VERSION+="${CHARS:RAND:1}"
done

echo "version-$VERSION" > version
echo "Generated version: version-$VERSION"

for f in *2021client.zip; do
    if [[ -f "$f" ]]; then
        mv "$f" "version-$VERSION-2021client.zip"
        echo "Renamed $f to version-$VERSION-2021client.zip"
    fi
done

pyinstaller \
    --onefile \
    --icon=assets/icon.ico \
    --name=BubbaversePlayerLinuxLauncher \
    --add-data="assets:assets" \
    --add-data="version:." \
    --add-data="version_info.txt:." \
    --console \
    --hidden-import=psutil \
    main.py

if [[ -f "dist/BubbaversePlayerLinuxLauncher" ]]; then
    cp "dist/BubbaversePlayerLinuxLauncher" "dist/version-$VERSION-BubbaversePlayerLinuxLauncher"
    echo "Build successful!"
    echo "Standard executable: dist/BubbaversePlayerLinuxLauncher"
    echo "Versioned executable: dist/version-$VERSION-BubbaversePlayerLinuxLauncher"
else
    echo "Build failed!"
    exit 1
fi 
