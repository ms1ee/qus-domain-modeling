"""Entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [--config path/to/config.json]
"""

import argparse
import logging
import os
import sys
from typing import List, Optional

if __package__ in (None, ""):
    # Allow running as a script: `python src/main.py`
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import system  # noqa: E402  pylint: disable=wrong-import-position
from input_manager import InputManager  # noqa: E402  pylint: disable=wrong-import-position


def configure_logging() -> None:
    """Configure logging from the DISPATCH_LOG_LEVEL environment variable."""
    level_name = os.environ.get("DISPATCH_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the simulator.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    configure_logging()
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None,
                        help="optional JSON file with system parameters")
    args = parser.parse_args(argv)

    if args.config:
        try:
            system.load_config(args.config)
        except (OSError, ValueError) as exc:
            print(f"Warning: could not load config '{args.config}': {exc}. "
                  "Using defaults.")

    system.init_system()
    try:
        InputManager().run()
    except Exception:  # last-resort recovery
        logging.getLogger(__name__).exception("Unexpected fatal error")
        print("A fatal error occurred. See the log for details.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
