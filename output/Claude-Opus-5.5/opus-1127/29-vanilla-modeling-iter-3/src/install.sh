#!/bin/sh
# One-click setup: verifies Python and runs the simulator.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 -c 'import sys; assert sys.version_info >= (3, 6), "Python 3.6+ required"'
echo "Installation complete. Starting simulator..."
exec python3 "$DIR/main.py" "$@"
