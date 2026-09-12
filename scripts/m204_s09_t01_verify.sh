#!/usr/bin/env bash
set -euo pipefail
python3 scripts/m204_s09_deadlock_note.py --check
printf '%s\n' 'S09 T01 VERIFY OK'
