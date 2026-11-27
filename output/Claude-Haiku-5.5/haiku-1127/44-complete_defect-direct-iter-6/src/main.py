"""Entry point for the Beijing Subway fare calculation CLI.

Run from any working directory, for example:
    python src/main.py --mode comprehensive --format json
"""

import os
import sys

# Make the sibling modules under src/ importable regardless of the working directory.
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from cli import main  # noqa: E402  (import after sys.path adjustment)


if __name__ == "__main__":
    sys.exit(main())
