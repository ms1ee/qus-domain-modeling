"""One-click setup: checks the Python version and writes a default config."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    """Verify environment and create config.json if missing."""
    if sys.version_info < (3, 6):
        print("Python 3.6+ is required.")
        return 1
    path = os.path.join(HERE, "config.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"initial_funds": 1000, "rider_cost": 300,
                       "rider_speed": 10, "spawn_x": 435, "spawn_y": 385},
                      fh, indent=2)
        print("Created default config.json")
    print("Installation complete. Run: python %s" %
          os.path.join(HERE, "main.py"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
