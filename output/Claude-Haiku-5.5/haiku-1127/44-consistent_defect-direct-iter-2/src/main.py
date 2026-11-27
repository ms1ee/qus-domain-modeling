"""Entry point of the Beijing Subway fare calculation system.

Usage:
    python src/main.py [--mode MODE] [--format text|json] [--output_file PATH]
                       [--max_transfers N] [--line_preference "Line 1"] [--check_data]
"""

import sys

from cli import run_cli


if __name__ == "__main__":
    sys.exit(run_cli())
