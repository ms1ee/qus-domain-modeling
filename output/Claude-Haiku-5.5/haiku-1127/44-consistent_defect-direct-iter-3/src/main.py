"""
Entry point of the Beijing Subway fare calculation system.

Usage (from any working directory):
    python src/main.py [--mode MODE] [--format text|json] [--output_file PATH]
                       [--max_transfers N] [--line_preference LINE] [--check_data]
"""

import os
import sys

# Make the flat top-level modules under src/ importable regardless of the CWD.
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
