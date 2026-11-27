"""Entry point of the food delivery dispatch simulator command-line tool.

Run with ``python src/main.py``. Each loop iteration processes one command
and then advances the simulation by one tick.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402
from system import SystemManager, init_system  # noqa: E402

logger = logging.getLogger("dispatch")

BANNER = (
    "Food Delivery Order Dispatch Simulator\n"
    "Type 'help' for commands. Map: 8x8 grid, 800x800 units, funds start at 1000."
)


def main():
    """Run the interactive main loop until the user quits.

    Returns:
        Process exit code (0 on normal termination).
    """
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    init_system()
    system = SystemManager()
    display = DisplayManager(system)
    manager = InputManager(system, display)

    print(BANNER)
    while system.is_running:
        try:
            line = input("dispatch> ")
        except (EOFError, KeyboardInterrupt):
            print()
            system.stop()
            break

        try:
            output = manager.execute(line)
        except Exception:  # error recovery: never crash the main loop
            logger.exception("Command execution failed")
            output = "Unexpected internal error; system state preserved. See log for details."

        if output:
            print(output)

        if system.is_running:
            try:
                system.tick()
            except Exception:
                logger.exception("Tick failed")
                print("Internal error during tick; the simulation continues.")

    print("Simulator stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
