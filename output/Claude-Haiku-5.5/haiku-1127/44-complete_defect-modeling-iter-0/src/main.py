"""Entry point of the Beijing Subway fare calculation system.

Run with ``python src/main.py`` (or ``python -m src.main`` from the project root).
"""

import os
import sys

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
