"""Entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [--config CONFIG_JSON] [--debug]
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import system  # noqa: E402
from input_manager import InputManager  # noqa: E402


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Optional list of arguments (defaults to ``sys.argv[1:]``).

    Returns:
        The parsed ``argparse.Namespace``.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None,
                        help="path to a JSON file with system parameters")
    parser.add_argument("--debug", action="store_true",
                        help="enable debug logging to stderr")
    return parser.parse_args(argv)


def main(argv=None):
    """Run the simulator.

    Args:
        argv: Optional list of command-line arguments.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    system.init_system(args.config)
    InputManager().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
