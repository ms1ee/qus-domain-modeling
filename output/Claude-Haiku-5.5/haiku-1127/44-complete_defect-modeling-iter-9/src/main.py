"""Entry point for the Beijing Subway Fare Calculation System.

Run from any directory, for example:
    python src/main.py --format json --mode least_transfer
    python -m src.main --check_data
"""
import os
import sys

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from cli import main  # noqa: E402  (import after sys.path adjustment)


if __name__ == "__main__":
    sys.exit(main())
