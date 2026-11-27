"""Entry point for the food delivery dispatch simulator."""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system import SystemManager  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default="config.json", help="JSON config file")
    parser.add_argument("--load", default=None, help="load saved state JSON")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    manager = SystemManager(config_path=args.config)
    if args.load:
        try:
            manager.load_state(args.load)
        except (OSError, ValueError) as exc:
            print(f"Could not load state: {exc}")
    manager.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
