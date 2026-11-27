#!/usr/bin/env sh
# One-click installation / launch helper for the Food Delivery Dispatch Simulator.
# Only the Python standard library is required (Python 3.6+, 3.8+ recommended).
set -e
PY=${PYTHON:-python3}
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "Python 3 was not found. Please install Python 3.8+ first."
    exit 1
fi
"$PY" -c "import sys; assert sys.version_info >= (3, 6), 'Python 3.6+ required'"
DIR=$(cd "$(dirname "$0")" && pwd)
if [ ! -f "$DIR/config.json" ]; then
    cat > "$DIR/config.json" <<EOF
{
  "initial_funds": 1000,
  "recruitment_cost": 500,
  "recruitment_threshold": 300,
  "rider_speed": 10,
  "rider_start_x": 400,
  "rider_start_y": 400
}
EOF
    echo "Created default configuration at $DIR/config.json"
fi
echo "Installation complete. Run with: $PY $DIR/main.py --config $DIR/config.json"
