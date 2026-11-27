"""Entry point for the food delivery dispatch simulator.

Run with ``python src/main.py [--config config.json]``.
"""

import argparse
import logging
import os
import sys

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402
from system import init_system  # noqa: E402


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Optional list of arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed :class:`argparse.Namespace`.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None,
                        help="JSON file with initial_funds, rider_recruitment_cost "
                             "and max_riders")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    return parser.parse_args(argv)


def main(argv=None):
    """Run the interactive simulator.

    Args:
        argv: Optional command-line arguments.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    system = init_system(args.config)
    manager = InputManager(system, DisplayManager())
    manager.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
