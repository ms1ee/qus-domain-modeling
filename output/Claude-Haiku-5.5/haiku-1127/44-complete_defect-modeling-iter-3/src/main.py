"""Entry point of the Beijing Subway fare calculation system.

Run from any directory with:
    python src/main.py [--output_file PATH] [--format text|json]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1"]
                       [--check_data]
"""

import os
import sys

# Make the sibling modules importable regardless of the working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
