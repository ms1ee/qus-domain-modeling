"""Command-line entry point for the food delivery dispatch simulator.

Run with: ``python src/main.py``

Each iteration of the main loop processes one user command and then advances
the simulation by one tick. The ``tick n`` command advances n extra ticks.
"""

import logging
import math
import os
import sys

from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from path_planner import PathPlanner
from system import SystemManager, init_system

logger = logging.getLogger("fds")

DEFAULT_STATE_FILE = "dispatch_state.json"
MAX_TICKS_PER_COMMAND = 10000
WELCOME = ("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units). "
           "Type 'help' for commands.")


def _setup_logging():
    """Configure logging; level can be set with FDS_LOG_LEVEL."""
    level_name = os.environ.get("FDS_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def handle_start(args, ui, display):
    """Dispatch a new order and print the assignment summary and route map.

    Args:
        args: Optional command arguments with the four coordinates.
        ui: InputManager used to prompt when no arguments are given.
        display: DisplayManager used for rendering.

    Returns:
        None
    """
    if args:
        values = InputManager.parse_coordinates(args)
    else:
        values = ui.prompt_coordinates()
    restaurant = (values[0], values[1])
    customer = (values[2], values[3])
    order = OrderManager.create_order(restaurant, customer)
    result = OrderManager.dispatch(order)
    rider = result["rider"]
    if rider is None:
        print(f"Order #{order.id} is pending: no rider is available and "
              "funds are insufficient.")
        return
    planner = PathPlanner()
    rx, ry = order.res_pos
    cx, cy = order.cus_pos
    to_restaurant = planner.plan_route(rider.x, rider.y, rx, ry)
    to_customer = planner.plan_route(rx, ry, cx, cy)
    route = to_restaurant + to_customer[1:]
    distance = planner.path_length(route)
    eta = math.ceil(distance / rider.speed) if rider.speed else 0
    print(display.render_start_summary(order, rider, result["new_rider"],
                                       distance, eta))
    print(display.render_map(SystemManager.get_riders(), [order], route))


def execute(command, args, ui, display):
    """Run one parsed command.

    Args:
        command: Normalised command name.
        args: Argument tokens.
        ui: InputManager instance.
        display: DisplayManager instance.

    Returns:
        None

    Raises:
        ValueError: For invalid user input (reported to the user).
    """
    if command == "":
        return
    if command == "start":
        handle_start(args, ui, display)
    elif command == "status":
        print(display.render_status(SystemManager.get_funds(),
                                    SystemManager.get_riders(),
                                    SystemManager.check_consistency()))
    elif command == "orders":
        print(display.render_orders(OrderManager.all_orders()))
    elif command == "riders":
        print(display.render_rider_log(SystemManager.get_riders()))
    elif command == "map":
        print(display.render_map(SystemManager.get_riders(),
                                 OrderManager.all_orders()))
    elif command == "tick":
        count = int(args[0]) if args else 1
        if not 1 <= count <= MAX_TICKS_PER_COMMAND:
            raise ValueError(f"tick count must be 1-{MAX_TICKS_PER_COMMAND}")
        for _ in range(count):
            SystemManager.tick()
        print(f"Simulated time is now tick {SystemManager.current_tick()}.")
    elif command == "save":
        path = SystemManager.save_state(args[0] if args
                                        else DEFAULT_STATE_FILE)
        print(f"State saved to {path}.")
    elif command == "load":
        path = args[0] if args else DEFAULT_STATE_FILE
        try:
            issues = SystemManager.load_state(path)
        except FileNotFoundError:
            raise ValueError(f"file not found: {path}")
        except OSError as exc:
            raise ValueError(f"cannot read {path}: {exc}")
        print(f"State loaded from {path}.")
        for issue in issues:
            print(f"Warning: {issue}")
    elif command == "history":
        entries = ui.history[-20:]
        print("\n".join(f"{i + 1:>3}: {line}"
                        for i, line in enumerate(entries)) or "No history.")
    elif command == "help":
        print(ui.help_text())
    elif command in ("quit", "exit"):
        SystemManager.stop()
    else:
        raise ValueError(f"unknown command '{command}'. Type 'help'.")


def main():
    """Run the interactive dispatch simulator.

    Returns:
        int: Process exit code.
    """
    _setup_logging()
    init_system()
    ui = InputManager()
    display = DisplayManager()
    print(WELCOME)
    while SystemManager.is_running():
        try:
            command, args = ui.read_command()
        except (EOFError, KeyboardInterrupt):
            print()
            SystemManager.stop()
            break
        try:
            execute(command, args, ui, display)
        except ValueError as exc:
            print(f"Error: {exc}")
        except Exception as exc:  # error recovery: keep the loop alive
            logger.exception("Unexpected failure while running '%s'", command)
            print(f"Unexpected error: {exc}. Continuing with current state.")
        if SystemManager.is_running():
            SystemManager.tick()
    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
