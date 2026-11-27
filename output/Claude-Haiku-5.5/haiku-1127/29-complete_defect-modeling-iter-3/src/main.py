"""Command-line entry point for the Food Delivery Order Dispatch Simulator."""

import argparse
import logging
import sys

from input_manager import InputManager
from system import STATE_FILE, init_system


def configure_logging(debug: bool) -> None:
    """Configure root logging.

    Args:
        debug: When True, log at DEBUG level; otherwise WARNING.
    """
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv=None) -> int:
    """Run the simulator.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    parser.add_argument("--state-file", default=STATE_FILE,
                        help="path of the JSON file where state is saved on exit")
    args = parser.parse_args(argv)
    configure_logging(args.debug)
    logger = logging.getLogger("main")

    try:
        system = init_system()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Initialisation failed")
        print(f"Fatal error during initialisation: {exc}")
        return 1

    try:
        InputManager(system).run()
    finally:
        try:
            system.save_state(args.state_file)
            print(f"State saved to {args.state_file}")
        except OSError as exc:
            print(f"Warning: could not save state: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
