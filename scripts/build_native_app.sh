#!/usr/bin/env bash
# Build the native app and DMG; retain prior artifacts. Exit 0 on success, 1 on failure.
# Usage: scripts/build_native_app.sh [--app-only | --help]
set -euo pipefail
IFS=$'\n\t'

if [[ "${1:-}" == "--help" ]]; then
    echo 'Build BoardVault native app and dist/BoardVault-native.dmg (requires uv and Swift tools).'
    exit 0
fi
APP_ONLY=false
if [[ "${1:-}" == "--app-only" ]]; then APP_ONLY=true; shift; fi
if [[ $# -ne 0 || "$(uname -s)" != Darwin ]]; then
    echo 'Requires macOS; accepts --app-only or --help.' >&2
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCH="x86_64" # Change to universal2 when Python and all bundled binaries support both architectures.
PY="${PROJECT_DIR}/.venv-native-build/bin/python"
PACKAGE="${PROJECT_DIR}/native/BoardVault"
export UV_CACHE_DIR="${PROJECT_DIR}/build/uv-cache"
export PYINSTALLER_CONFIG_DIR="${PROJECT_DIR}/build/pyinstaller-cache"
export CLANG_MODULE_CACHE_PATH="${PROJECT_DIR}/build/clang-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="${PROJECT_DIR}/build/swift-module-cache"
export PYTHON_DOTENV_DISABLED=1
export MACOSX_DEPLOYMENT_TARGET=13.0

if [[ ! -x "${PY}" ]]; then
    UV_PYTHON_INSTALL_DIR="${PROJECT_DIR}/build/python-runtime" \
        uv venv --managed-python --python 3.13 "${PROJECT_DIR}/.venv-native-build"
fi
# Reuse an already matching environment without contacting a package registry.
if ! "${PY}" - "${PROJECT_DIR}/native/requirements-build.txt" <<'PYTHON'
import importlib.metadata
import pathlib
import sys
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    name, wanted = line.split("==", 1)
    try:
        actual = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        sys.exit(1)
    if actual != wanted:
        sys.exit(1)
PYTHON
then
    uv pip sync --python "${PY}" "${PROJECT_DIR}/native/requirements-build.txt"
fi
SWIFT_ARCH=(--arch "${ARCH}")
if [[ "${ARCH}" == universal2 ]]; then
    SWIFT_ARCH=(--arch x86_64 --arch arm64)
fi
swift build --disable-sandbox --cache-path "${PROJECT_DIR}/build/swift-cache" --package-path "${PACKAGE}" -c release "${SWIFT_ARCH[@]}"
BIN_DIR="$(swift build --disable-sandbox --cache-path "${PROJECT_DIR}/build/swift-cache" --package-path "${PACKAGE}" -c release "${SWIFT_ARCH[@]}" --show-bin-path)"
mkdir -p "${PROJECT_DIR}/build" "${PROJECT_DIR}/dist/native"
STAGE="$(mktemp -d "${PROJECT_DIR}/build/native.XXXXXX")"
APP="${STAGE}/BoardVault.app"
RESOURCES="${APP}/Contents/Resources"
mkdir -p "${APP}/Contents/MacOS" "${RESOURCES}"

BOARDVAULT_BUILD_ARCH="${ARCH}" "${PY}" -m PyInstaller --noconfirm \
    --distpath "${STAGE}/engine-dist" --workpath "${STAGE}/engine-work" \
    "${PROJECT_DIR}/native/boardvault-engine.spec"

cp "${BIN_DIR}/BoardVault" "${APP}/Contents/MacOS/BoardVault"
ditto "${STAGE}/engine-dist/boardvault-engine" "${RESOURCES}/engine"
cp "${PROJECT_DIR}/native/resources/app.icns" "${RESOURCES}/app.icns"
cp "${PROJECT_DIR}/args/config.json" "${RESOURCES}/config.json"
cp "${PROJECT_DIR}/LICENSE" "${RESOURCES}/LICENSE"
cat > "${APP}/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>BoardVault</string>
<key>CFBundleDisplayName</key><string>BoardVault</string>
<key>CFBundleIdentifier</key><string>com.subkoks.boardvault.native</string>
<key>CFBundleExecutable</key><string>BoardVault</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>2.0.0</string>
<key>CFBundleVersion</key><string>20004</string>
<key>CFBundleIconFile</key><string>app.icns</string>
<key>LSMinimumSystemVersion</key><string>13.0</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSPrincipalClass</key><string>NSApplication</string>
</dict></plist>
PLIST
plutil -lint "${APP}/Contents/Info.plist"
"${PY}" "${PROJECT_DIR}/scripts/verify_native_bundle.py" "${APP}" "${ARCH}"
# Local ad-hoc signature only; no Developer ID, notarization, or paid tooling.
codesign --force --deep --sign - "${APP}"
codesign --verify --deep --strict "${APP}"
STAMP="$(date +%Y%m%d-%H%M%S)"
FINAL_APP="${PROJECT_DIR}/dist/native/BoardVault.app"
FINAL_DMG="${PROJECT_DIR}/dist/BoardVault-native.dmg"
if [[ -e "${FINAL_APP}" ]]; then mv "${FINAL_APP}" "${STAGE}/previous-BoardVault-${STAMP}.app"; fi
mv "${APP}" "${FINAL_APP}"
echo "Built: ${FINAL_APP}"
if [[ "${APP_ONLY}" == true ]]; then
    echo 'App-only build: any existing DMG belongs to an earlier build.'
    exit 0
fi
if ! "${PY}" -m dmgbuild -s "${PROJECT_DIR}/src/gui/packaging/dmg_settings.py" \
    -D app="${FINAL_APP}" BoardVault "${STAGE}/BoardVault-native.dmg"; then
    echo 'App is ready; DMG creation failed. Any existing DMG is an earlier build.' >&2
    exit 1
fi
if [[ -e "${FINAL_DMG}" ]]; then mv "${FINAL_DMG}" "${STAGE}/previous-BoardVault-${STAMP}.dmg"; fi
mv "${STAGE}/BoardVault-native.dmg" "${FINAL_DMG}"
echo "Built: ${FINAL_DMG}"
echo 'Ad-hoc signed for local use; not Developer ID signed or notarized.'
