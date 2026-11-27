#!/usr/bin/env sh
# One-click installation / run helper for the Food Delivery Dispatch Simulator.
# No third-party dependencies are required (standard library only).
set -e
PYTHON=${PYTHON:-python3}
"$PYTHON" -c "import sys; assert sys.version_info >= (3, 6), 'Python 3.6+ required'"
echo "Python version OK. No external dependencies needed."
echo "Run the simulator with:  $PYTHON $(dirname "$0")/main.py"
