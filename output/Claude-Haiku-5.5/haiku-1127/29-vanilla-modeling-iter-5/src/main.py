"""Entry point for the Food Delivery Order Dispatch simulator.

Usage:
    python src/main.py [--config path/to/config.json] [--debug]
"""

import argparse
import logging
import sys
from typing import List, Optional

from display import DisplayManager
from input_manager import InputManager
from system import init_system


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list; defaults to ``sys.argv[1:]``.

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None, help="path to a JSON configuration file")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the simulator.

    Args:
        argv: Optional argument list.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    system = init_system(args.config)

    import config

    level_name = "DEBUG" if args.debug else str(config.CONFIG.get("log_level", "WARNING")).upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.WARNING),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    display = DisplayManager(system)
    manager = InputManager(system, display)
    manager.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
