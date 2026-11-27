"""Entry point for the Food Delivery Order Dispatch System simulator.

Usage:
    python src/main.py [config.json]

If no configuration file is given, ``dispatch_config.json`` in the current
directory is used when it exists.
"""

import logging
import os
import sys

from input_manager import InputManager
from system import init_system

DEFAULT_CONFIG_PATH = "dispatch_config.json"


def main(argv=None):
    """Configure logging, initialise the system and run the command loop.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    argv = sys.argv[1:] if argv is None else argv
    level_name = os.environ.get("DISPATCH_LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.WARNING),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if argv:
        config_path = argv[0]
    elif os.path.exists(DEFAULT_CONFIG_PATH):
        config_path = DEFAULT_CONFIG_PATH
    else:
        config_path = None
    init_system(config_path)
    InputManager().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
