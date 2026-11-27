"""Entry point of the Beijing Subway fare calculation CLI.

Usage (from the project root or any directory):
    python src/main.py [--format text|json] [--mode MODE] [--max_transfers N]
                       [--line_preference "Line 1"] [--output_file PATH] [--check_data]
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from cli import run  # noqa: E402


def main(argv=None) -> int:
    """Run the CLI and return the process exit code."""
    return run(argv)


if __name__ == "__main__":
    sys.exit(main())
