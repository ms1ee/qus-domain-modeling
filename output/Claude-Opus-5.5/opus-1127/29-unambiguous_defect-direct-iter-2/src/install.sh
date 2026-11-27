#!/bin/sh
# One-click setup: checks Python and launches the simulator.
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required."; exit 1; }
cd "$(dirname "$0")" || exit 1
echo "No third-party dependencies needed. Starting simulator..."
python3 main.py "$@"
