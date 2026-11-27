"""Entry point: run with `python src/main.py [options]`."""

import os
import sys

# Make the modules in src/ importable with plain names regardless of working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
