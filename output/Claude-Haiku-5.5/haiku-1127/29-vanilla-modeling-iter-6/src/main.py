"""Entry point for the Food Delivery Order Dispatch System simulator.

Usage:
    python src/main.py [--config path/to/config.json] [--debug]
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from input_manager import InputManager  # noqa: E402
from system import init_system  # noqa: E402


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Optional argument list; defaults to ``sys.argv[1:]``.

    Returns:
        The parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(
        description="Food delivery order dispatch simulator.")
    parser.add_argument("--config", default=None,
                        help="Optional JSON configuration file.")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging to stderr.")
    return parser.parse_args(argv)


def main(argv=None):
    """Configure logging, build the system and run the command loop.

    Args:
        argv: Optional argument list for testing.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(level=level,
                        format="%(asctime)s %(levelname)s %(name)s: "
                               "%(message)s")
    try:
        system = init_system(args.config)
        InputManager(system).run()
    except Exception:
        logging.getLogger(__name__).exception("Fatal error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
