#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd "$PWD/check-saved-references.py" > saved-reference-check.log 2>&1
python3 verify.py
