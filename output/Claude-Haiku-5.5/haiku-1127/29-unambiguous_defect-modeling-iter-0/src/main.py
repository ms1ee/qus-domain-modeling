"""Entry point for the food delivery dispatch simulator.

Run with ``python src/main.py`` from the project root. Each iteration of the
main loop reads one command, executes it and then advances simulated time by
one tick.

Environment variables:
    DISPATCH_CONFIG     Path to the JSON configuration file
                        (default: dispatch_config.json).
    DISPATCH_LOG_LEVEL  Logging level (default: WARNING).
"""

import logging
import os
import sys

from display import DisplayManager
from input_manager import InputManager
from system import init_system, load_config

DEFAULT_CONFIG_PATH = "dispatch_config.json"
BANNER = ("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)\n"
          "Type 'help' for commands, 'quit' to exit.")


def _setup_logging():
    """Configure logging to stderr using DISPATCH_LOG_LEVEL."""
    level_name = os.environ.get("DISPATCH_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(level=level,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        stream=sys.stderr)


def _setup_readline():
    """Enable line editing and history where the readline module exists."""
    try:
        import readline  # noqa: F401  (side effect: enables history keys)
    except ImportError:
        pass


def main():
    """Run the interactive simulation loop.

    Returns:
        int: Process exit status.
    """
    _setup_logging()
    _setup_readline()
    logger = logging.getLogger("dispatch.main")
    config_path = os.environ.get("DISPATCH_CONFIG", DEFAULT_CONFIG_PATH)
    config = load_config(config_path)
    system = init_system(config)
    display = DisplayManager()
    commands = InputManager(system, display)
    print(BANNER)
    while system.is_running:
        try:
            line = input("dispatch> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            output = commands.execute(line)
        except Exception:  # keep the loop alive on unexpected errors
            logger.exception("unexpected error while executing command")
            output = "Internal error occurred; the simulation state was preserved."
        if output:
            print(output)
        if system.is_running:
            try:
                system.advance_tick(1)
            except Exception:
                logger.exception("unexpected error while advancing tick")
    print(f"Simulation ended at tick {system.current_tick}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
