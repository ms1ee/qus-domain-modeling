"""Command-line entry point for the food delivery dispatch simulator.

Run from the project root with::

    python src/main.py [--config FILE] [--save FILE] [--debug] [--log-file FILE]

Each iteration of the main loop reads one command.  Commands that advance
the simulation run one tick per unit (``wait n`` runs n ticks), and every
tick moves all riders and assigns any queued orders.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Allow both ``python src/main.py`` and ``python -m main`` from within src/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402
from persistence import save_state  # noqa: E402
from system import SystemManager  # noqa: E402

logger = logging.getLogger("dispatch")

WELCOME = (
    "Food Delivery Dispatch Simulator\n"
    "Map: 800x800 units, 8x8 grid of 100x100 cells. "
    "Type 'help' for commands."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        argparse.Namespace: Parsed options.
    """
    parser = argparse.ArgumentParser(
        description="Command-line food delivery dispatch simulator.")
    parser.add_argument("--config", help="JSON file with parameter overrides")
    parser.add_argument("--save", help="write a JSON snapshot on exit")
    parser.add_argument("--log-file", help="write detailed logs to this file")
    parser.add_argument("--debug", action="store_true",
                        help="print debug logs to stderr")
    return parser.parse_args(argv)


def setup_logging(debug: bool, log_file: str | None) -> None:
    """Configure the dispatch logger.

    Args:
        debug: Whether to send debug output to stderr.
        log_file: Optional file receiving debug-level logs.
    """
    root = logging.getLogger("dispatch")
    root.handlers.clear()
    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s")

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if debug else logging.ERROR)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError as exc:
            print(f"Warning: cannot open log file {log_file}: {exc}",
                  file=sys.stderr)


def run_loop(system: SystemManager, inp: InputManager,
             reader=input, writer=print) -> None:
    """Run the interactive main loop until the system stops.

    Args:
        system: The SystemManager instance.
        inp: The InputManager instance.
        reader: Callable that reads one line of input.
        writer: Callable that prints output.
    """
    while system.running:
        try:
            line = reader("> ")
        except (EOFError, KeyboardInterrupt):
            writer("")
            break
        try:
            text, ticks = inp.execute(line)
        except Exception:  # noqa: BLE001 - keep the session alive
            logger.exception("Unexpected error for command %r", line)
            text = ("Internal error: the command could not be completed. "
                    "System state has been preserved.")
            ticks = 0
        if text:
            writer(text)
        for _ in range(ticks):
            if not system.running:
                break
            try:
                events = system.advance_tick()
            except Exception:  # noqa: BLE001
                logger.exception("Simulation tick failed")
                events = []
            for event in events:
                writer(DisplayManager.format_event(event))


def run(argv: list[str] | None = None) -> int:
    """Program entry point.

    Args:
        argv: Optional argument list.

    Returns:
        int: Process exit status.
    """
    args = parse_args(argv)
    setup_logging(args.debug, args.log_file)

    if args.config:
        applied = config.load_config(args.config)
        if applied:
            print(f"Loaded configuration overrides: {applied}")

    system = SystemManager()
    display = DisplayManager()
    inp = InputManager(system, display, reader=input)

    print(WELCOME)
    run_loop(system, inp)

    if args.save:
        if save_state(args.save, system):
            print(f"State saved to {args.save}.")
        else:
            print(f"Warning: could not save state to {args.save}.")
    print(f"Simulation ended at tick {system.tick}.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
