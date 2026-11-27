"""Entry point of the Beijing Subway fare calculation system.

Run with either::

    python -m src.main [options]     (from the project root)
    python src/main.py [options]
"""

import sys

try:
    from .cli import main
except ImportError:  # pragma: no cover - src/ directory used directly on sys.path
    from cli import main


if __name__ == "__main__":
    sys.exit(main())
