"""Entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys

from config import Configuration
from system import SystemManager


def main(argv=None):
    """Parse arguments and run the interactive simulator."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="path to JSON configuration file")
    parser.add_argument("--load", nargs="?", const="", default=None,
                        help="load saved state (optional file path)")
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    manager = SystemManager(Configuration(args.config))
    if args.load is not None:
        try:
            manager.load_state(args.load or None)
            print("State loaded.")
        except (OSError, ValueError, KeyError) as exc:
            print("Could not load state: %s" % exc)
    manager.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
