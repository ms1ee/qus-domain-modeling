#!/usr/bin/env sh
# One-click installation / launch helper for the Food Delivery Dispatch Simulator.
# Only the Python standard library is required.
set -e
PYTHON_BIN="${PYTHON:-python3}"
"$PYTHON_BIN" -c "import sys; assert sys.version_info >= (3, 6), 'Python 3.6+ required'"
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ ! -f "$DIR/config.json" ]; then
  cat > "$DIR/config.json" <<EOF
{
  "initial_funds": 1000,
  "recruitment_cost": 300,
  "rider_speed": 10,
  "spawn_x": 435,
  "spawn_y": 385
}
EOF
  echo "Created default configuration at $DIR/config.json"
fi
echo "Installation complete. Run with: $PYTHON_BIN $DIR/main.py --config $DIR/config.json"
