"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import math
import sys
from typing import List

import globalvar
from display import DisplayManager
from input_manager import CommandError, Command, InputManager
from order import NoRiderAvailableError, assign_order, cancel_order, create_order
from pathplanner import PathPlanner
from rider import IDLE, STATE_NAMES
from system import advance_tick, get_riders, init_system, save_state

logger = logging.getLogger("dispatch")
DEFAULT_SAVE_FILE = "simulation_state.json"

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy]  [n] Create an order (restaurant then customer); prompts if omitted
  status               [s] Funds, riders, states and order lists
  orders               [o] Details of all orders
  riders               [r] Every recorded rider status change
  map                  [m] ASCII map of the grid with riders and orders
  tick [n]             [t] Advance the simulation by n ticks (default 1)
  history              [l] Show command history
  save [file]          [w] Save state to a JSON file
  help                 [h] Show this help
  quit / exit          [q] Leave the program
  !!                       Repeat the previous command"""


def _print_new_events(tick: int) -> None:
    """Print rider events that occurred at ``tick``."""
    for rider in get_riders():
        for entry in rider.log:
            if entry["tick"] == tick:
                order = "-" if entry["order_id"] is None else entry["order_id"]
                print(f"  [t={tick}] Rider {rider.rider_id}: {entry['event']} "
                      f"(order {order}) at ({entry['x']},{entry['y']})")


def handle_start(inp: InputManager, display: DisplayManager, cmd: Command) -> None:
    """Create and assign an order, then print the grid info and route map."""
    coords = cmd.arguments if cmd.arguments else inp.ask_coordinates()
    res = (coords[0], coords[1])
    cus = (coords[2], coords[3])

    riders_before = len(get_riders())
    order = create_order(res, cus)
    try:
        rider = assign_order(order)
    except NoRiderAvailableError as exc:
        cancel_order(order)
        print(f"Order could not be assigned: {exc}.")
        return

    new_rider = len(get_riders()) > riders_before
    rider_pos = rider.snapped_position()
    to_restaurant = PathPlanner.plan(rider_pos, order.res_pos)
    to_customer = PathPlanner.plan(order.res_pos, order.cus_pos)
    route = [rider_pos] + to_restaurant + to_customer

    print(f"Order {order.id} created at tick {order.start_time}.")
    print(f"Restaurant: input ({res[0]},{res[1]}) -> grid cell "
          f"({order.restaurant_x // 100},{order.restaurant_y // 100}), "
          f"centre ({order.restaurant_x},{order.restaurant_y})")
    print(f"Customer:   input ({cus[0]},{cus[1]}) -> grid cell "
          f"({order.customer_x // 100},{order.customer_y // 100}), "
          f"centre ({order.customer_x},{order.customer_y})")
    print(f"New rider recruited: {'yes' if new_rider else 'no'}")
    print(f"Assigned to rider {rider.rider_id} (state: {STATE_NAMES[rider.state]}, "
          f"queued orders: {len(rider.orders)}).")
    print(display.render_route_summary(order, rider, route))
    print(display.render_map(riders=[rider], orders=[order], route=route))


def handle_tick(count: int, display: DisplayManager) -> None:
    """Advance the simulation and print the events that happened."""
    for _ in range(count):
        tick = advance_tick()
        _print_new_events(tick)
    print(f"Simulation now at tick {globalvar.get_value('tick', 0)}.")


def handle_save(cmd: Command) -> None:
    """Save the simulation state to the requested or default file."""
    path = cmd.raw_args[0] if cmd.raw_args else DEFAULT_SAVE_FILE
    try:
        save_state(path)
        print(f"State saved to {path}.")
    except OSError as exc:
        print(f"Error: could not save state: {exc}")


def dispatch(cmd: Command, inp: InputManager, display: DisplayManager) -> None:
    """Route a parsed command to its handler.

    Args:
        cmd: The parsed command.
        inp: Input manager (used for prompts and history).
        display: Display manager (used for output).
    """
    name = cmd.name
    if name == "start":
        handle_start(inp, display, cmd)
    elif name == "status":
        print(display.render_status(globalvar.get_value("tick", 0),
                                    globalvar.get_value("funds", 0), get_riders()))
    elif name == "orders":
        print(display.render_orders(globalvar.get_value("orders", [])))
    elif name == "riders":
        print(display.render_rider_events(get_riders()))
    elif name == "map":
        print(display.render_map(riders=get_riders(), orders=globalvar.get_value("orders", [])))
    elif name == "tick":
        handle_tick(cmd.arguments[0] if cmd.arguments else 1, display)
    elif name == "history":
        if not inp.command_history:
            print("No commands entered yet.")
        for index, line in enumerate(inp.command_history, start=1):
            print(f"  {index:>3}  {line}")
    elif name == "save":
        handle_save(cmd)
    elif name == "help":
        print(HELP_TEXT)
    elif name in ("quit", "exit"):
        globalvar.set_value("is_running", False)
        print("Goodbye.")


def run_loop(inp: InputManager, display: DisplayManager) -> None:
    """Run the interactive read-dispatch loop until the system stops."""
    while globalvar.get_value("is_running", False):
        try:
            line = inp.read_line("dispatch> ")
        except CommandError as exc:
            print(f"Error: {exc}")
            continue
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        try:
            cmd = inp.parse(line)
            dispatch(cmd, inp, display)
        except CommandError as exc:
            print(f"Error: {exc}")
        except Exception:  # noqa: BLE001 - keep the simulator alive
            logger.exception("Unexpected error while executing '%s'", line)
            print("An unexpected error occurred; the system state has been preserved.")


def main(argv: List[str] = None) -> int:
    """Program entry point.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    init_system()
    inp = InputManager()
    display = DisplayManager()
    print("Food Delivery Order Dispatch System")
    print("Type 'help' for commands. Map is 800x800 with 100-unit cells.")
    run_loop(inp, display)
    return 0


if __name__ == "__main__":
    sys.exit(main())
