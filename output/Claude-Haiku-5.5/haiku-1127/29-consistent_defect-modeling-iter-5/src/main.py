"""Entry point for the Food Delivery Order Dispatch System simulator.

Run with:  python src/main.py
"""

import logging
import sys

from input_manager import InputManager
from system import init_system


def main() -> int:
    """Initialize the system and start the interactive command loop.

    Returns:
        Process exit code (0 on normal exit).
    """
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    init_system()
    InputManager().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
