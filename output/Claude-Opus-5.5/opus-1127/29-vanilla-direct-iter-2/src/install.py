"""One-click installation helper: checks Python version and writes a config."""

import os
import sys

from config import write_default_config


def main():
    """Verify the environment and create a default config.json."""
    if sys.version_info < (3, 6):
        print("Python 3.6+ is required.")
        return 1
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.exists(path):
        write_default_config(path)
        print("Wrote default configuration to %s" % path)
    else:
        print("Configuration already exists at %s" % path)
    print("No third-party dependencies required. Run: python main.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
