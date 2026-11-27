"""Entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [--config PATH] [--debug]
"""

import argparse
import logging
import sys
from typing import Optional, Sequence

from input_manager import InputManager
from system import init_system

logger = logging.getLogger("dispatch")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv (sequence[str] | None): Arguments; defaults to sys.argv.

    Returns:
        argparse.Namespace: Parsed options.
    """
    parser = argparse.ArgumentParser(
        description="Command-line food delivery dispatch simulator.")
    parser.add_argument("--config", default=None,
                        help="path to a JSON configuration file")
    parser.add_argument("--debug", action="store_true",
                        help="enable debug logging to stderr")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Initialise the system and run the interactive loop.

    Args:
        argv (sequence[str] | None): Command-line arguments.

    Returns:
        int: Process exit code (0 on normal exit, 1 on startup failure).
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        import readline  # noqa: F401 - enables line editing and history
    except ImportError:
        pass
    try:
        system = init_system(args.config)
    except Exception:  # noqa: BLE001 - report startup failure cleanly
        logger.exception("Failed to initialise the system.")
        print("Startup failed; see the log for details.")
        return 1
    InputManager(system).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
