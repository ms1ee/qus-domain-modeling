"""Allow running the package with ``python -m lottery_system`` from ``src/``."""

import sys

from lottery_system.cli import main

if __name__ == "__main__":
    sys.exit(main())
