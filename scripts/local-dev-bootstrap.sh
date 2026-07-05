#!/usr/bin/env bash
# local-dev-bootstrap.sh — local equivalent of cloud-setup (deps + .env skeleton).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
log() { printf '[bootstrap] %s\n' "$*"; }

cd "$ROOT"

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  log ".env copied from .env.example"
fi

log "uv sync --extra dev,gui"
uv sync --extra dev,gui

uv run python -c "import tg_schematic_downloader; print('import ok')"
log "[DONE] apple-all-schematic bootstrapped."
