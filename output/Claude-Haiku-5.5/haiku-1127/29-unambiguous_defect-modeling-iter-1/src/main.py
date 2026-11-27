"""Entry point for the Food Delivery Order Dispatch System simulator.

Run with:  python src/main.py
"""

import json
import logging
import os
import sys

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

import config  # noqa: E402
from input_manager import build_input_manager  # noqa: E402
from system import init_system  # noqa: E402


def setup_logging():
    """Configure file logging for debugging and diagnostics."""
    try:
        logging.basicConfig(
            filename=config.SETTINGS["log_file"],
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    except OSError:
        logging.basicConfig(level=logging.WARNING)


def main(argv=None):
    """Run the interactive dispatch simulator.

    Args:
        argv: Unused placeholder for command-line arguments.

    Returns:
        Process exit code.
    """
    setup_logging()
    try:
        if config.load_config():
            logging.getLogger(__name__).info("Loaded configuration overrides")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Warning: could not read configuration file, using defaults ({exc}).")
    init_system()
    manager = build_input_manager()
    try:
        manager.run()
    except Exception:  # Last-resort recovery: report and exit cleanly.
        logging.getLogger(__name__).exception("Fatal error in main loop")
        print("A fatal error occurred. See the log file for details.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
