"""Entry point: python src/main.py [options]

Adds the src directory to sys.path so that the top-level modules can be imported
regardless of the current working directory.
"""

import os
import sys

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
