"""Entry point for the Beijing Subway fare calculation system.

Usage:
    python src/main.py [--format text|json] [--mode MODE] [--max_transfers N]
                       [--line_preference "Line 1"] [--output_file PATH]
                       [--check_data]
"""

import sys

from cli import main

if __name__ == "__main__":
    sys.exit(main())
