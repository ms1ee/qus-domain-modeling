"""Entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [config.json] [--debug]
"""

import logging
import sys
from typing import List, Optional

import storage
from display import DisplayManager
from input_manager import InputManager
from system import init_system

DEFAULT_CONFIG = "config.json"


def main(argv: Optional[List[str]] = None) -> int:
    """Run the interactive dispatch simulator.

    Args:
        argv: Command-line arguments excluding the program name.

    Returns:
        Process exit code (0 on normal termination).
    """
    if argv is None:
        argv = sys.argv[1:]
    debug = "--debug" in argv
    positional = [a for a in argv if not a.startswith("--")]
    config_path = positional[0] if positional else DEFAULT_CONFIG

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        system = init_system()
        storage.load_config(config_path)
        display = DisplayManager()
        manager = InputManager(system, display)
        manager.run()
    except Exception:  # top-level safety net
        logging.getLogger(__name__).exception("fatal error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
