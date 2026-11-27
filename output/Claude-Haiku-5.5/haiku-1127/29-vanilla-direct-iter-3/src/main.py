"""Entry point for the Food Delivery Order Dispatch System simulator.

Usage:
    python src/main.py [--config config.json] [--save state.json] [--debug]
"""

import argparse
import logging
import sys
from typing import List, Optional

from input_manager import InputManager
from system import init_system


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        The parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="Food delivery order dispatch simulator (CLI).")
    parser.add_argument("--config", default=None,
                        help="JSON file with system parameter overrides.")
    parser.add_argument("--save", default=None,
                        help="JSON file to write the final system state to.")
    parser.add_argument("--log-file", default=None,
                        help="Write log output to this file instead of stderr.")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging.")
    return parser.parse_args(argv)


def configure_logging(debug: bool, log_file: Optional[str]) -> None:
    """Configure the root logger.

    Args:
        debug: Use DEBUG level when True, otherwise WARNING.
        log_file: Optional log file path.
    """
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        filename=log_file,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the simulator.

    Args:
        argv: Optional argument list.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    configure_logging(args.debug, args.log_file)
    system = init_system(args.config)
    try:
        InputManager(system).run()
    finally:
        if args.save:
            system.save_state(args.save)
    return 0


if __name__ == "__main__":
    sys.exit(main())
