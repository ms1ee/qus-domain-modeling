"""
Program entry point.

Run with:  python src/main.py [options]
Works from any working directory because the src/ directory is added to
sys.path before the project modules are imported.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
