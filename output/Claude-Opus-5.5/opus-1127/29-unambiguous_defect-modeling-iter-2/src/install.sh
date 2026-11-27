#!/usr/bin/env sh
# One-click installation/configuration script for the dispatch simulator.
# The program only needs the standard library, so this script just checks
# the Python version and writes a default configuration file.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

"$PYTHON" -c "import sys; assert sys.version_info >= (3, 6), 'Python 3.6+ required'"
echo "Python version OK."

if [ ! -f "$DIR/config.json" ]; then
  "$PYTHON" -c "import json, sys; sys.path.insert(0, '$DIR'); \
from config import DEFAULT_CONFIG; \
json.dump(DEFAULT_CONFIG, open('$DIR/config.json', 'w'), indent=2)"
  echo "Default configuration written to $DIR/config.json"
fi

echo "Installation complete. Run with: $PYTHON $DIR/main.py --config $DIR/config.json"
