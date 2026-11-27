"""Entry point for the food delivery dispatch simulator."""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system import init_system  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="path to JSON configuration file")
    parser.add_argument("--load", action="store_true",
                        help="restore state from the state file")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    manager = init_system(args.config)
    if args.load:
        print("State loaded." if manager.load_state() else "No saved state loaded.")
    manager.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
