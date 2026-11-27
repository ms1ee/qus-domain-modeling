"""Program entry point. Run from the project root with: python -m src.main"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
