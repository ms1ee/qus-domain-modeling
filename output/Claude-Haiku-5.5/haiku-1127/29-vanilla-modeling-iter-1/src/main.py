"""Command line entry point for the food delivery dispatch simulator.

Usage:
    python main.py [--config path/to/config.json] [--debug]
"""

import logging
import math
import sys
from typing import Callable, Dict, List, Optional

import globalvar
from display import DisplayManager
from input_manager import InputManager
from path_planner import to_cell_index
from system import SystemManager, export_state, init_system, load_config

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant and customer coordinates 0-800).
                       Without arguments you will be prompted for them.
  status (s)           Show system funds and every rider's status.
  orders (o)           Show all orders with time, distance and rider.
  riders (r)           Show the status change log of every rider.
  tick [n] (t)         Advance the simulation by n ticks (default 1).
  map (m)              Show the ASCII map with riders and active orders.
  save [path]          Save riders, orders and configuration to JSON.
  history (hist)       Show the command history.
  !!                   Repeat the last command.
  help (h, ?)          Show this help.
  quit (q) / exit (x)  Leave the program."""


def cmd_start(manager: SystemManager, inp: InputManager, args: List[str]) -> None:
    """Create an order, show the assigned rider's route and the map."""
    if args and len(args) != 4:
        raise ValueError("start expects 4 integers: restaurant_x restaurant_y customer_x customer_y")
    if args:
        coords = inp.parse_coordinates(args)
    else:
        coords = inp.prompt_coordinates(input)
        if coords is None:
            print("Order entry cancelled.")
            return

    order, added = manager.submit_order((coords[0], coords[1]), (coords[2], coords[3]))
    rx, ry = order.raw_restaurant
    cx, cy = order.raw_customer
    print(f"Order #{order.id} created at tick {order.start_time}.")
    print(f"Restaurant: input ({rx},{ry}) -> grid cell "
          f"({to_cell_index(rx)},{to_cell_index(ry)}), centre {order.res_center}")
    print(f"Customer:   input ({cx},{cy}) -> grid cell "
          f"({to_cell_index(cx)},{to_cell_index(cy)}), centre {order.cus_center}")
    print(f"New rider added: {'yes' if added else 'no'} (funds: {manager.funds})")

    if order.rider_id is None:
        print("No rider available yet; the order stays pending in the queue.")
        return

    rider = manager.get_rider(order.rider_id)
    route = manager.path_planner.plan_route((rider.x, rider.y), order.res_center, order.cus_center)
    eta = math.ceil(len(route) / rider.speed) if route else 0
    print(f"Assigned rider: #{rider.rider_id} at ({rider.x},{rider.y}), speed {rider.speed} units/tick")
    print(f"Route length: {len(route)} units, estimated time: {eta} ticks "
          f"(use 'tick' to advance the simulation)")
    print(manager.display.render_map(riders=[rider], orders=[order], route=route))


def cmd_status(manager: SystemManager, inp: InputManager, args: List[str]) -> None:
    """Show the system snapshot."""
    print(manager.display.format_status(manager.funds, manager.riders, manager.pending_count))


def cmd_orders(manager: SystemManager, inp: InputManager, args: List[str]) -> None:
    """Show the order table."""
    print(manager.display.format_orders(manager.order_manager.orders))


def cmd_riders(manager: SystemManager, inp: InputManager, args: List[str]) -> None:
    """Show every rider's status change log."""
    print(manager.display.format_rider_logs(manager.riders))


def cmd_tick(manager: SystemManager, inp: InputManager, args: List[str]) -> None:
    """Advance the simulation by one or more ticks and print the events."""
    count = 1
    if args:
        try:
            count = int(args[0])
        except ValueError:
            raise ValueError("tick count must be an integer") from None
    if not 1 <= count <= 1000:
        raise ValueError("tick count must be between 1 and 1000")
    for _ in range(count):
        events = manager.tick()
        for rider_id, entry in events:
            order_text = "" if entry["order_id"] is None else f" (order #{entry['order_id']})"
            print(f"  t={entry['tick']} rider {rider_id}: {entry['event']}{order_text} "
                  f"at ({entry['x']},{entry['y']})")
    print(f"Current tick: {manager.current_tick}, funds: {manager.funds}, "
          f"riders: {len(manager.riders)}, pending: {manager.pending_count}")


def cmd_map(manager: SystemManager, inp: InputManager, args: List[str]) -> None:
    """Show the ASCII map with riders and active orders."""
    print(manager.display.render_map(riders=manager.riders,
                                     orders=manager.order_manager.orders))


def cmd_save(manager: SystemManager, inp: InputManager, args: List[str]) -> None:
    """Save the state to a JSON file."""
    path = args[0] if args else "dispatch_state.json"
    export_state(path)
    print(f"State saved to {path}")


def cmd_history(manager: SystemManager, inp: InputManager, args: List[str]) -> None:
    """Print the command history."""
    if not inp.commandHistory:
        print("No commands yet.")
        return
    for index, command in enumerate(inp.commandHistory, start=1):
        print(f"{index:>4}  {command}")


def cmd_help(manager: SystemManager, inp: InputManager, args: List[str]) -> None:
    """Print the help text."""
    print(HELP_TEXT)


def build_handlers() -> Dict[str, Callable[[SystemManager, InputManager, List[str]], None]]:
    """Return the mapping from command name to handler."""
    return {
        "start": cmd_start,
        "status": cmd_status,
        "orders": cmd_orders,
        "riders": cmd_riders,
        "tick": cmd_tick,
        "map": cmd_map,
        "save": cmd_save,
        "history": cmd_history,
        "help": cmd_help,
    }


def _parse_config_argument(argv: List[str]) -> Optional[str]:
    """Return the path given with --config, or None."""
    if "--config" not in argv:
        return None
    index = argv.index("--config")
    if index + 1 >= len(argv):
        raise ValueError("--config requires a file path")
    return argv[index + 1]


def main(argv: Optional[List[str]] = None) -> int:
    """Run the interactive simulator.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Process exit code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    level = logging.DEBUG if "--debug" in args else logging.WARNING
    logging.basicConfig(level=level,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        config_path = _parse_config_argument(args)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    init_system()
    if config_path:
        load_config(config_path)

    manager = SystemManager()
    inp = InputManager()
    handlers = build_handlers()

    print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
    print("Type 'help' for the list of commands.")

    while manager.is_running:
        try:
            line = inp.read_command()
        except ValueError as exc:
            print(f"Error: {exc}")
            continue
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line is None:
            continue

        try:
            name, command_args = inp.parse_command(line)
        except ValueError as exc:
            print(f"Error: {exc}")
            continue

        if name in ("quit", "exit"):
            manager.is_running = False
            break

        handler = handlers.get(name)
        if handler is None:
            print(f"Unknown command '{name}'. Type 'help' for the list of commands.")
            continue
        try:
            handler(manager, inp, command_args)
        except ValueError as exc:
            print(f"Error: {exc}")
        except Exception:
            logger.exception("Command '%s' failed", name)
            print("An unexpected error occurred; the system state has been preserved.")
            manager.check_consistency()

    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
