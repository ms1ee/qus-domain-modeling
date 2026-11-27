"""Entry point for the Beijing Subway fare calculation CLI.

Usage:
    python src/main.py [--output_file PATH] [--format text|json]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1"] [--check_data]
"""

import os
import sys

# Make sibling modules importable regardless of the working directory.
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from cli import run_cli  # noqa: E402


def main(argv=None) -> int:
    """Run the command-line application and return its exit code."""
    return run_cli(argv)


if __name__ == "__main__":
    sys.exit(main())
