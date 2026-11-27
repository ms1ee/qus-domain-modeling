"""Entry point for the Beijing Subway fare calculation CLI.

Run with:  python src/main.py [--output_file PATH] [--format text|json]
           [--mode shortest_distance|least_transfer|comprehensive]
           [--max_transfers N] [--line_preference "Line 1"] [--check_data]
"""

import os
import sys

# Make the modules in this directory importable regardless of the working directory.
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
