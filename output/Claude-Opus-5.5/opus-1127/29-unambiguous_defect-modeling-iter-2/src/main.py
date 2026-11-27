"""Entry point of the food delivery dispatch simulator."""

import argparse
import logging
import sys

from config import load_config
from manager import SystemManager


def main(argv=None):
    """Parse arguments, build the system and run the main loop."""
    parser = argparse.ArgumentParser(
        description="Food delivery order dispatch simulator")
    parser.add_argument("--config", default="config.json",
                        help="JSON configuration file")
    parser.add_argument("--debug", action="store_true",
                        help="enable debug logging")
    parser.add_argument("--no-save", action="store_true",
                        help="do not save state on exit")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    manager = SystemManager(load_config(args.config),
                            save_on_exit=not args.no_save)
    manager.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
