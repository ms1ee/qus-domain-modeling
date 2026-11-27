"""Entry point for the Food Delivery Order Dispatch System simulator.

Run from the project root with::

    python src/main.py [--config dispatch_config.json] [--log-level INFO]
"""

import argparse
import logging
import sys
from typing import List, Optional

import system
from display import DisplayManager
from input_manager import InputManager
from system import SystemManager

DEFAULT_CONFIG_PATH = "dispatch_config.json"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line options.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed namespace with ``config`` and ``log_level``.
    """
    parser = argparse.ArgumentParser(
        description="Food delivery order dispatch simulator")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH,
                        help="JSON file with system parameters")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="logging verbosity written to stderr")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Initialise the system and run the interactive command loop.

    Args:
        argv: Optional argument list for testing.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stderr,
    )
    system.init_system()
    manager = SystemManager()
    manager.load_config(args.config)
    display = DisplayManager()
    cli = InputManager(manager, display)
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
    except Exception:
        logging.getLogger("dispatch").exception("Fatal error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
