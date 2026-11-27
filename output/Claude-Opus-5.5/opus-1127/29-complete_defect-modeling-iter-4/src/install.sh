#!/bin/sh
# One-click setup: verifies Python and runs the simulator.
# No third-party dependencies are required.
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"
"$PY" -c "import sys; assert sys.version_info >= (3, 6)" || {
    echo "Python 3.6+ is required"; exit 1; }
echo "Installation complete. Starting the simulator..."
cd "$DIR" && exec "$PY" main.py "$@"
