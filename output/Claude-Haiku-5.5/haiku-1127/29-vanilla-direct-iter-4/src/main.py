"""Entry point for the Food Delivery Order Dispatch System simulator.

Run with ``python src/main.py`` (or ``python -m main`` from inside ``src``).
"""

import argparse
import logging
import os
import sys

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from input_manager import InputManager  # noqa: E402
from system import init_system  # noqa: E402


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--debug", action="store_true",
                        help="enable debug logging to stderr")
    return parser.parse_args(argv)


def main(argv=None):
    """Start the interactive simulator.

    Args:
        argv: Optional argument list.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        system = init_system()
        InputManager(system).run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
    except Exception:  # last-resort guard so the program exits cleanly
        logging.getLogger("dispatch").exception("Fatal error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
