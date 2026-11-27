"""Entry point for the Beijing Subway fare calculation system.

Usage (from the project root):
    python src/main.py [--mode MODE] [--format text|json] [--output_file PATH]
                       [--max_transfers N] [--line_preference "Line 1"] [--check_data]
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
