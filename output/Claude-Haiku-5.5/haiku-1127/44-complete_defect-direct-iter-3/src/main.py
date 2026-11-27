"""
Program entry point.

Run with:
    python src/main.py [--output_file PATH] [--format text|json]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1"] [--check_data]
"""

import sys

from cli import main

if __name__ == "__main__":
    sys.exit(main())
