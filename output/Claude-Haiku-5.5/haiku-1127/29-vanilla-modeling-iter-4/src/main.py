"""Command-line entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [--config config.json] [--log-level WARNING]
                       [--log-file path]
"""

import argparse
import logging
import sys

from input_manager import InputManager
from system import init_system, load_config

logger = logging.getLogger(__name__)


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed ``argparse.Namespace``.
    """
    parser = argparse.ArgumentParser(
        description="Food delivery order dispatch simulator (8x8 grid).")
    parser.add_argument("--config", default="config.json",
                        help="JSON file with system parameters")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="logging verbosity")
    parser.add_argument("--log-file", default=None,
                        help="write logs to this file instead of stderr")
    return parser.parse_args(argv)


def main(argv=None):
    """Run the simulator.

    Args:
        argv: Optional argument list.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        filename=args.log_file,
    )
    config = load_config(args.config)
    try:
        system = init_system(config)
    except Exception:
        logger.exception("System initialisation failed")
        return 1
    manager = InputManager(system)
    manager.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
