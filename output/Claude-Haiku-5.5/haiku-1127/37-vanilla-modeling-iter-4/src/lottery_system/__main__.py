"""Entry point: run with `python -m lottery_system` from the src directory."""

import sys

from lottery_system.cli import LotteryApp


def main() -> int:
    return LotteryApp().run()


if __name__ == "__main__":
    sys.exit(main())
