"""Entry point: run `python src/main.py` from any directory."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
