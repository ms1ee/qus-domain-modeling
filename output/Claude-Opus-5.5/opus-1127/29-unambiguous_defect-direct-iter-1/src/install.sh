#!/bin/sh
# One-click setup: checks Python and runs the simulator.
python3 --version || { echo "Python 3 is required"; exit 1; }
cd "$(dirname "$0")" && python3 main.py "$@"
