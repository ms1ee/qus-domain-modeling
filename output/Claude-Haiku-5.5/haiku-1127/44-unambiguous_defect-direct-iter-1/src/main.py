"""Entry point for the Beijing Subway fare calculation CLI.

Run with either:
    python src/main.py --mode comprehensive
    python -m src.main --mode comprehensive
"""

import os
import sys

# Make sibling modules importable (plain imports) regardless of how this file is launched.
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
