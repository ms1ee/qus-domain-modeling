"""Command-line entry point for the food delivery dispatch simulator.

Run with:  python src/main.py [--config path/to/config.json] [--debug]
"""

import argparse
import logging
import sys

from config import load_config
from input_manager import CommandError
from system import init_system

BANNER = (
    "Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)\n"
    "Type 'help' for commands, 'quit' to exit."
)


def _enable_line_editing():
    """Enable arrow-key history editing when the readline module is available."""
    try:
        import readline  # noqa: F401  (imported for its side effects)
    except ImportError:
        pass


def run(argv=None, reader=input, writer=print):
    """Run the interactive command loop.

    Args:
        argv: Optional list of command-line arguments.
        reader: Callable that reads a line of input.
        writer: Callable that writes output text.

    Returns:
        int: Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None, help="path to a JSON configuration file")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _enable_line_editing()

    system = init_system(load_config(args.config))
    writer(BANNER)

    while system.is_running:
        try:
            line = reader("dispatch> ")
        except (EOFError, KeyboardInterrupt):
            writer("")
            break
        try:
            command, command_args = system.input_manager.parse(line)
            if command is None:
                continue
            writer(system.execute(command, command_args, reader=reader))
        except CommandError as exc:
            writer("Error: %s" % exc)
        except (EOFError, KeyboardInterrupt):
            writer("")
            break
        except Exception as exc:  # keep the simulator alive on unexpected errors
            logging.getLogger(__name__).exception("unexpected error")
            writer("Unexpected error: %s (system state preserved)" % exc)

    system.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(run())
