"""Entry point: ``python src/main.py`` or ``python -m src.main`` from the project root."""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
