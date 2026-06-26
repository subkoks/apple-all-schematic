#!/usr/bin/env bash
# Build the macOS .app bundle with PyInstaller.
#
#   ./scripts/build_macos.sh
#
# Output: dist/Apple Schematic Downloader.app
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

if ! python -c "import PySide6" >/dev/null 2>&1; then
    echo "GUI deps missing. Run: pip install -e \".[gui]\"" >&2
    exit 1
fi

if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "Installing PyInstaller…" >&2
    pip install pyinstaller
fi

echo "Cleaning previous build…"
rm -rf build dist

echo "Building…"
pyinstaller --noconfirm apple-schematic-gui.spec

echo
echo "Done: dist/Apple Schematic Downloader.app"
