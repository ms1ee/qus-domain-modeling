"""Entry point: python -m lottery_system (with src/ on PYTHONPATH)."""
import sys

from lottery_system.cli import main

if __name__ == "__main__":
    sys.exit(main())
