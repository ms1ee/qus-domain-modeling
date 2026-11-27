"""Entry point: ``python -m src`` from the project root."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
