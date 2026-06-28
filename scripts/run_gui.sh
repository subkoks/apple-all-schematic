#!/usr/bin/env bash
# Launch the BoardVault desktop GUI in development.
#
#   ./scripts/run_gui.sh
#
# Requires the GUI extras:  pip install -e ".[gui]"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${PROJECT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec python -m gui.app "$@"
