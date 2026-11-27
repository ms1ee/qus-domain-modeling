"""Command-line entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [--config path/to/config.json] [--debug]
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

import config
from input_manager import InputManager
from system import init_system

logger = logging.getLogger("dispatch")

WELCOME_TEXT = (
    "Food Delivery Order Dispatch System\n"
    "Map: 8x8 grid, 800x800 units. Type 'help' for commands, 'quit' to exit."
)


def setup_logging(debug: bool) -> None:
    """Configure application logging.

    Args:
        debug: When True, debug-level messages are printed to stderr.
    """
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the interactive dispatch simulator.

    Args:
        argv: Optional command-line arguments (defaults to sys.argv).

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None,
                        help="path to a JSON configuration file")
    parser.add_argument("--debug", action="store_true",
                        help="enable debug logging")
    args = parser.parse_args(argv)

    setup_logging(args.debug)
    config.configure(args.config)
    system = init_system()
    manager = InputManager(system)
    print(WELCOME_TEXT)

    while system.is_running:
        try:
            line = input("dispatch> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            output = manager.handle(line)
        except Exception:  # keep the simulator alive on unexpected errors
            logger.exception("Unexpected error while handling command %r", line)
            issues = system.verify_state()
            output = ("An internal error occurred; the system state was checked"
                      + (f" and {len(issues)} issue(s) repaired." if issues else "."))
        if output:
            print(output)

    try:
        path = system.save_history()
        print(f"State saved to {path}.")
    except OSError as exc:
        print(f"Warning: could not save state: {exc}")
    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
