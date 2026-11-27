"""Program entry point.

Run from the project root with:
    python src/main.py [--mode ...] [--format ...] [--output_file ...] ...
"""

import sys

from cli import main

if __name__ == "__main__":
    sys.exit(main())
