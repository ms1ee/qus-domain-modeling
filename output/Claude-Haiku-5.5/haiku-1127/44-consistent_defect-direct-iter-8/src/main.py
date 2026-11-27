"""Program entry point: ``python src/main.py [options]`` works from any directory."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
