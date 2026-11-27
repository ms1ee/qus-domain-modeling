"""Program entry point.

Run with:  python src/main.py [--format text|json] [--mode MODE] ...
"""

import sys

from cli import main

if __name__ == "__main__":
    sys.exit(main())
