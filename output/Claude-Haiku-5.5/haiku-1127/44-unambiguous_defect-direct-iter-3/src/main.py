"""Entry point of the Beijing Subway fare calculation system.

Usage:
    python src/main.py [--mode MODE] [--format text|json] [--output_file PATH]
                       [--max_transfers N] [--line_preference LINE] [--check_data]
"""

import sys

from cli import main


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(130)
