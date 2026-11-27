"""Program entry point: ``python src/main.py [options]``."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
