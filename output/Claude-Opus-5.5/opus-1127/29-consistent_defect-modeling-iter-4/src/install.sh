#!/bin/sh
# One-click setup: verifies Python and launches the simulator.
command -v python3 >/dev/null 2>&1 || { echo "python3 is required"; exit 1; }
cd "$(dirname "$0")" && python3 main.py
