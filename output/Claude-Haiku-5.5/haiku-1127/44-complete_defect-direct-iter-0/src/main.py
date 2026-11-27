"""Entry point of the Beijing Subway fare calculation system.

Usage (from the repository root):
    python src/main.py [--output_file PATH] [--format text|json]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1"]
                       [--check_data]
"""

import os
import sys

# Make sibling modules importable regardless of the current working directory.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from cli import main  # noqa: E402  (import after sys.path adjustment)

if __name__ == "__main__":
    sys.exit(main())
