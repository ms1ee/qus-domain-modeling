"""Command-line entry point for the food delivery dispatch simulator.

Run with::

    python src/main.py [--config config.json] [--state dispatch_state.json]
                       [--debug] [--no-save]

Each loop iteration reads one command, executes it and then advances the
simulated clock by one tick.
"""

import argparse
import logging
import sys
from typing import List, Optional

import config
import globalvar
from display import DisplayManager
from input_manager import InputManager
from system import SystemManager, get_manager, init_system

logger = logging.getLogger("dispatch")

BANNER = (
    "Food Delivery Order Dispatch System\n"
    "8x8 grid, 800x800 units. Type 'help' for commands."
)
MAX_TICK_COMMAND = 1000
CONSISTENCY_CHECK_INTERVAL = 1


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=BANNER.splitlines()[0])
    parser.add_argument(
        "--config", default="config.json",
        help="JSON file with system parameter overrides",
    )
    parser.add_argument(
        "--state", default=None,
        help="JSON file used to save the final state (overrides config)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="enable debug logging"
    )
    parser.add_argument(
        "--no-save", action="store_true", help="do not save state on exit"
    )
    return parser.parse_args(argv)


def setup_logging(log_file: str, debug: bool) -> None:
    """Configure file logging; fall back to stderr if the file is unusable."""
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    try:
        logging.basicConfig(filename=log_file, level=level, format=fmt)
    except OSError:
        logging.basicConfig(level=logging.WARNING, format=fmt)


def run_ticks(manager: SystemManager, display: DisplayManager,
              steps: int) -> None:
    """Advance the simulation and print delivery notifications."""
    for _ in range(steps):
        completed = manager.tick()
        for order in completed:
            print(
                f"[tick {manager.tick_count}] Order #{order.id} delivered by "
                f"rider #{order.rider_id} (took {order.time_taken} tick(s))"
            )


def cmd_start(manager: SystemManager, display: DisplayManager,
              input_mgr: InputManager, tokens: List[str]) -> None:
    """Handle ``start``: place an order and show the assignment."""
    if tokens:
        coords = input_mgr.parse_coordinates(tokens)
    else:
        coords = input_mgr.request_order_coordinates()
    if coords is None:
        print("Order cancelled.")
        return
    result = manager.process_order((coords[0], coords[1]),
                                   (coords[2], coords[3]))
    print(display.render_order_result(result, manager.riders))


def cmd_tick(manager: SystemManager, display: DisplayManager,
             tokens: List[str]) -> None:
    """Handle ``tick [n]``: advance the clock n ticks."""
    steps = 1
    if tokens:
        if len(tokens) != 1 or not tokens[0].isdigit():
            raise ValueError("tick expects a positive integer count")
        steps = int(tokens[0])
    if not 1 <= steps <= MAX_TICK_COMMAND:
        raise ValueError(f"tick count must be between 1 and "
                         f"{MAX_TICK_COMMAND}")
    run_ticks(manager, display, steps)


def execute(command: str, tokens: List[str], manager: SystemManager,
            display: DisplayManager, input_mgr: InputManager) -> bool:
    """Dispatch a parsed command.

    Returns:
        True if the command should advance the clock by one tick.
    """
    if command == "start":
        cmd_start(manager, display, input_mgr, tokens)
    elif command == "status":
        print(display.render_status(manager.funds, manager.tick_count,
                                    manager.riders,
                                    len(manager.order_manager.pending)))
    elif command == "orders":
        print(display.render_orders(manager.all_orders()))
    elif command == "riders":
        print(display.render_rider_log(manager.riders))
    elif command == "map":
        print(display.render_map(manager.riders, manager.active_orders()))
    elif command == "tick":
        cmd_tick(manager, display, tokens)
        return False
    elif command == "help":
        print(display.render_help())
    elif command == "quit":
        globalvar.set_value("running", False)
        return False
    return True


def check_consistency(manager: SystemManager) -> None:
    """Verify state and recover automatically if inconsistencies exist."""
    problems = manager.verify_state()
    if not problems:
        return
    for problem in problems:
        logger.warning("Consistency problem: %s", problem)
    fixes = manager.repair_state()
    for fix in fixes:
        logger.info("Recovery: %s", fix)
    print(f"Note: {len(problems)} state inconsistency(ies) detected and "
          "automatically recovered.")


def save_final_state(manager: SystemManager, path: str) -> None:
    """Persist the system state to a JSON file, reporting any failure."""
    try:
        config.save_state(path, manager.export_state())
        print(f"State saved to {path}.")
    except (OSError, TypeError, ValueError) as exc:
        logger.error("Could not save state: %s", exc)
        print(f"Warning: could not save state: {exc}")


def main(argv: Optional[List[str]] = None) -> int:
    """Run the interactive dispatch simulator.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    try:
        if config.load_config(args.config):
            print(f"Configuration loaded from {args.config}.")
    except (OSError, ValueError) as exc:
        print(f"Warning: could not load config '{args.config}': {exc}. "
              "Using default parameters.")
        config.CONFIG.update(config.DEFAULT_CONFIG)
    setup_logging(str(config.CONFIG["log_file"]), args.debug)

    init_system()
    manager = get_manager()
    display = DisplayManager()
    input_mgr = InputManager()
    print(BANNER)
    print(f"Starting funds: {manager.funds}, riders: {len(manager.riders)}")

    while globalvar.get_value("running", True):
        try:
            line = input_mgr.read_command()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        try:
            command, tokens = input_mgr.parse_command(line)
        except ValueError as exc:
            print(f"Error: {exc}. Type 'help' for the command list.")
            continue

        advance = True
        try:
            advance = execute(command, tokens, manager, display, input_mgr)
        except ValueError as exc:
            print(f"Input error: {exc}")
            advance = False
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unexpected error running '%s'", command)
            print(f"Unexpected internal error: {exc}. Attempting recovery.")
            manager.repair_state()
            advance = False

        check_consistency(manager)
        if advance and globalvar.get_value("running", True):
            run_ticks(manager, display, 1)

    if not args.no_save:
        state_path = args.state or str(config.CONFIG["state_file"])
        save_final_state(manager, state_path)
    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
