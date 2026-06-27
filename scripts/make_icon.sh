#!/usr/bin/env bash
# Generate src/gui/resources/app.icns from a rendered 1024px PNG.
# Uses only built-in macOS tools (sips, iconutil) plus PySide6.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

if [[ "$(uname)" != "Darwin" ]]; then
    echo "make_icon.sh requires macOS (sips/iconutil)." >&2
    exit 1
fi

PY="${PROJECT_DIR}/.venv/bin/python"
[[ -x "${PY}" ]] || PY="python3"

BUILD_DIR="${PROJECT_DIR}/build"
ICONSET="${BUILD_DIR}/app.iconset"
PNG="${BUILD_DIR}/icon_1024.png"
OUT_DIR="${PROJECT_DIR}/src/gui/resources"
OUT="${OUT_DIR}/app.icns"

mkdir -p "${ICONSET}" "${OUT_DIR}"

echo "Rendering 1024px master…"
"${PY}" "${SCRIPT_DIR}/make_icon.py" "${PNG}" 1024

echo "Building iconset…"
for size in 16 32 64 128 256 512 1024; do
    sips -z "${size}" "${size}" "${PNG}" --out "${ICONSET}/icon_${size}x${size}.png" >/dev/null
done
# Retina (@2x) variants
cp "${ICONSET}/icon_32x32.png"   "${ICONSET}/icon_16x16@2x.png"
cp "${ICONSET}/icon_64x64.png"   "${ICONSET}/icon_32x32@2x.png"
cp "${ICONSET}/icon_256x256.png" "${ICONSET}/icon_128x128@2x.png"
cp "${ICONSET}/icon_512x512.png" "${ICONSET}/icon_256x256@2x.png"
cp "${ICONSET}/icon_1024x1024.png" "${ICONSET}/icon_512x512@2x.png"
# iconutil expects exactly the standard names; drop the bare 64 and 1024.
rm -f "${ICONSET}/icon_64x64.png" "${ICONSET}/icon_1024x1024.png"

echo "Packing .icns…"
iconutil -c icns "${ICONSET}" -o "${OUT}"

echo "Done: ${OUT}"
