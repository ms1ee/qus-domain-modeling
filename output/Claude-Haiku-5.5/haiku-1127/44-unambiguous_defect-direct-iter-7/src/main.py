"""Entry point for the Beijing Subway fare calculation CLI.

Usage (from any working directory):
    python src/main.py [--output_file PATH] [--format text|json]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1"]
                       [--check_data]
"""

import os
import sys

# Make the modules in this directory importable regardless of how the
# program is started (``python src/main.py`` or ``python -m src.main``).
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from cli import main  # noqa: E402  (import after sys.path adjustment)


def _configure_console() -> None:
    """Make sure Chinese station names can be printed on most consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


if __name__ == "__main__":
    _configure_console()
    sys.exit(main())
