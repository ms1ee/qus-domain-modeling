"""Entry point of the Food Delivery Order Dispatch simulator.

Run with::

    python src/main.py
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LOG_FORMAT  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402
from system import init_system  # noqa: E402


def main() -> int:
    """Initialise the system and run the interactive command loop.

    Returns:
        Process exit code.
    """
    logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT)
    try:
        system = init_system()
        ui = InputManager(system, DisplayManager())
        ui.run()
    except Exception:  # last-resort recovery with diagnostics
        logging.getLogger(__name__).exception("Fatal error in dispatch simulator")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
