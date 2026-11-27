"""Entry point for the Company Team Building Smart Lottery System.

Usage:
    python src/main.py
"""
import os
import sys

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from lottery_system.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
