"""Entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [--config CONFIG_JSON] [--debug]
"""

import argparse
import logging
import sys
from typing import List, Optional

from config import load_config
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from system import init_system


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser.

    Returns:
        Configured ``ArgumentParser``.
    """
    parser = argparse.ArgumentParser(
        description="Command-line food delivery dispatch simulator.")
    parser.add_argument("--config", metavar="PATH",
                        help="JSON file with system parameters.")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging to stderr.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Run the simulator.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    config = load_config(args.config) if args.config else None
    system = init_system(config)
    order_manager = OrderManager()
    display = DisplayManager(system, order_manager)
    shell = InputManager(system, order_manager, display)
    try:
        shell.run()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
