"""Entry point for the food delivery dispatch simulator command-line tool.

Usage:
    python src/main.py [--config config.json] [--debug] [--log-file path]
"""

import argparse
import logging
import sys
from typing import List, Optional

from display_manager import DisplayManager
from input_manager import InputManager
from system import init_system

logger = logging.getLogger("dispatch")

BANNER = (
    "Food Delivery Order Dispatch System (8x8 grid, 800x800 units)\n"
    "Type 'help' for commands, 'quit' to exit."
)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Argument list, or None to use ``sys.argv``.

    Returns:
        The parsed namespace.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None,
                        help="JSON file with system parameter overrides")
    parser.add_argument("--debug", action="store_true",
                        help="enable debug logging to stderr")
    parser.add_argument("--log-file", default=None,
                        help="write log output to this file")
    return parser.parse_args(argv)


def setup_logging(debug: bool, log_file: Optional[str]) -> None:
    """Configure logging handlers.

    Args:
        debug: Whether to emit DEBUG level messages.
        log_file: Optional file that receives log output.
    """
    level = logging.DEBUG if debug else logging.WARNING
    handlers: List[logging.Handler] = []
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    else:
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the interactive command loop.

    Args:
        argv: Optional argument list for testing.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    setup_logging(args.debug, args.log_file)
    try:
        system = init_system(args.config)
    except Exception:  # startup failure is reported and aborts cleanly
        logger.exception("System initialisation failed")
        print("Failed to initialise the system. See log for details.")
        return 1

    display = DisplayManager()
    manager = InputManager(system, display, reader=input)
    print(BANNER)

    while system.is_running:
        try:
            line = input("dispatch> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            output = manager.handle(line)
        except Exception:  # keep the loop alive on unexpected failures
            logger.exception("Unexpected error while handling input")
            output = "Unexpected error. The system continues running."
        if output:
            print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
