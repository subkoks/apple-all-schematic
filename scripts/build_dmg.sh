#!/usr/bin/env bash
# Build the macOS app bundle and a drag-to-install .dmg (unsigned).
#
#   ./scripts/build_dmg.sh
#
# Output: dist/BoardVault.dmg
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

if [[ "$(uname)" != "Darwin" ]]; then
    echo "build_dmg.sh requires macOS." >&2
    exit 1
fi

PY="${PROJECT_DIR}/.venv/bin/python"
[[ -x "${PY}" ]] || PY="python3"

APP_NAME="BoardVault"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${APP_NAME}.dmg"

if ! "${PY}" -c "import PySide6" >/dev/null 2>&1; then
    echo "GUI deps missing. Run: pip install -e \".[gui]\"" >&2
    exit 1
fi
if ! "${PY}" -c "import PyInstaller" >/dev/null 2>&1; then
    echo "Installing PyInstaller…" >&2
    "${PY}" -m pip install pyinstaller
fi
if ! "${PY}" -c "import dmgbuild" >/dev/null 2>&1; then
    echo "Installing dmgbuild…" >&2
    "${PY}" -m pip install dmgbuild
fi

# 1. Icon
if [[ ! -f "src/gui/resources/app.icns" ]]; then
    echo "Generating app icon…"
    "${SCRIPT_DIR}/make_icon.sh"
fi

# 2. App bundle
echo "Cleaning previous build…"
rm -rf build dist
echo "Building .app with PyInstaller…"
"${PY}" -m PyInstaller --noconfirm apple-schematic-gui.spec

if [[ ! -d "${APP_PATH}" ]]; then
    echo "Build failed: ${APP_PATH} not found." >&2
    exit 1
fi

# 3. DMG
echo "Building .dmg…"
"${PY}" -m dmgbuild \
    -s src/gui/packaging/dmg_settings.py \
    -D app="${APP_PATH}" \
    "${APP_NAME}" "${DMG_PATH}"

echo
echo "Done: ${DMG_PATH}"
echo
echo "This build is UNSIGNED. On first launch macOS Gatekeeper will block it."
echo "Open it once with either:"
echo "  • Right-click the app in /Applications → Open → Open, or"
echo "  • xattr -dr com.apple.quarantine \"/Applications/${APP_NAME}.app\""
