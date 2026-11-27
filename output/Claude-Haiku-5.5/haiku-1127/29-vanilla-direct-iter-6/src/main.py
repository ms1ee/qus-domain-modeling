"""Entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [--config config.json] [--log-level WARNING]
"""

import argparse
import logging
import sys

from display_manager import DisplayManager
from input_manager import InputManager
from persistence import load_config
from globalvar import set_value
from system import SystemManager, init_system


def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional list of arguments (defaults to sys.argv).

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument(
        "--config", default="config.json", help="JSON configuration file path"
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Start the simulator.

    Args:
        argv: Optional list of command-line arguments.

    Returns:
        Process exit code (0 on normal exit).
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    init_system()
    config = load_config(args.config)
    if "funds" in config:
        try:
            set_value("funds", int(config["funds"]))
        except (TypeError, ValueError):
            logging.getLogger(__name__).warning("Invalid 'funds' in configuration")

    system = SystemManager()
    display = DisplayManager()
    InputManager(system, display).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
