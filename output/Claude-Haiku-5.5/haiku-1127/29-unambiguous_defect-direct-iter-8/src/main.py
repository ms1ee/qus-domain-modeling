"""Command-line entry point for the food delivery dispatch simulator.

Usage::

    python src/main.py [--config config.json] [--log-file dispatch.log]

Pressing Enter on an empty line advances the simulation by one tick.  Each
pass through the main loop is one command or one tick.
"""

import argparse
import logging
import sys
from typing import List, Optional

from display import DisplayManager
from globalvar import get_value
from input_manager import InputError, InputManager
from order import OrderManager
from order_model import Order
from path_planner import grid_cell_of
from system import SystemManager, init_system, load_config, save_snapshot

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy]  (s)  Create an order: restaurant then customer coordinates (0-800).
                            Prompts for the four values when none are given.
  status               (st) Show system funds, riders, states and order lists.
  orders               (o)  Show every order with timing, distance and rider.
  riders               (r)  Show the event log of every rider.
  map                  (m)  Show the ASCII map with riders and active orders.
  tick [n]             (t)  Advance the simulation by n ticks (default 1).
                            Pressing Enter on an empty line also advances one tick.
  save [path]               Save the state to a JSON file (default dispatch_state.json).
  history                   Show recent commands.
  help                 (?)  Show this help.
  quit                 (q)  Exit the program (also: exit).
"""


class DispatchApp:
    """Interactive controller that wires managers together and runs the loop.

    Attributes:
        system: Shared SystemManager.
        order_manager: Creates and dispatches orders.
        inputs: Command parser and history.
        display: Report and map renderer.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialise global state and optionally apply a configuration file.

        Args:
            config_path: Optional JSON configuration path.
        """
        init_system()
        if config_path:
            try:
                load_config(config_path)
                print(f"Loaded configuration from {config_path}.")
            except ValueError as exc:
                print(f"Warning: {exc}. Using default parameters.")
        self.system = SystemManager()
        self.order_manager = OrderManager(self.system)
        self.inputs = InputManager()
        self.display = DisplayManager()
        self._commands = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "save": self.cmd_save,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }

    # ----- main loop -------------------------------------------------------
    def run(self) -> None:
        """Run the interactive loop until quit, EOF or interrupt."""
        print("Food Delivery Order Dispatch System. Type 'help' for commands.")
        while self.system.is_running():
            try:
                line = self.inputs.read_line("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            try:
                name, args = InputManager.parse_command(line)
                self.inputs.record(line)
                self._commands[name](args)
            except InputError as exc:
                print(f"Input error: {exc}")
            except LookupError as exc:
                print(f"Dispatch error: {exc}")
            except ValueError as exc:
                print(f"Error: {exc}")
            except Exception as exc:  # keep the simulation alive
                logger.exception("Unexpected failure while handling '%s'", line)
                print(f"Unexpected internal error ({exc}). System state preserved.")
        print("Goodbye.")

    # ----- commands --------------------------------------------------------
    def cmd_start(self, args: List[str]) -> None:
        """Create an order, dispatch it, and print the assignment and route map."""
        tokens = list(args)
        if not tokens:
            prompt = "Enter restaurant_x restaurant_y customer_x customer_y: "
            tokens = self.inputs.read_line(prompt).split()
        coords = InputManager.parse_coordinates(tokens)
        order = Order(coords[0:2], coords[2:4])
        rider, new_rider = self.order_manager.dispatch(order)

        route = OrderManager.full_route(rider, order)
        eta = OrderManager.eta_ticks(rider, route)

        print(f"Order #{order.id} created at tick {order.start_time}.")
        print(
            f"  Restaurant: input ({order.raw_res[0]}, {order.raw_res[1]}) -> "
            f"grid cell {grid_cell_of(order.res_pos)}, centre {order.res_pos}"
        )
        print(
            f"  Customer:   input ({order.raw_cus[0]}, {order.raw_cus[1]}) -> "
            f"grid cell {grid_cell_of(order.cus_pos)}, centre {order.cus_pos}"
        )
        if new_rider is not None:
            print(f"  New rider added: yes (rider #{new_rider.rider_id}, "
                  f"funds now {self.system.funds})")
        else:
            print("  New rider added: no")
        print(
            f"  Assigned rider: #{rider.rider_id} speed={rider.speed} units/tick "
            f"route distance={order.distance} units ETA~{eta} ticks"
        )
        print(self.display.render_map(
            self.system.riders,
            orders=get_value("orders", []),
            route=[rider.position()] + route,
        ))

    def cmd_status(self, args: List[str]) -> None:
        """Print the system status snapshot."""
        print(self.display.format_status(self.system.funds, self.system.tick,
                                         self.system.riders))

    def cmd_orders(self, args: List[str]) -> None:
        """Print every order's details."""
        print(self.display.format_orders(get_value("orders", [])))

    def cmd_riders(self, args: List[str]) -> None:
        """Print every rider's recorded status changes."""
        print(self.display.format_rider_logs(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map with riders and active orders."""
        print(self.display.render_map(self.system.riders,
                                      orders=get_value("orders", [])))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation by one or more ticks."""
        count = InputManager.parse_count(args, default=1, maximum=1000)
        for _ in range(count):
            self.system.advance_tick()
        active = sum(1 for o in get_value("orders", []) if o.status != "completed")
        print(f"Tick {self.system.tick}: {len(self.system.riders)} riders, "
              f"{active} active orders, funds {self.system.funds}.")
        issues = self.system.check_consistency()
        for issue in issues:
            print(f"Consistency warning: {issue}")
            logger.warning("Consistency issue: %s", issue)

    def cmd_save(self, args: List[str]) -> None:
        """Save the current state to a JSON file."""
        path = args[0] if args else "dispatch_state.json"
        try:
            save_snapshot(path)
            print(f"State saved to {path}.")
        except OSError as exc:
            print(f"Error: could not save to '{path}': {exc}")

    def cmd_history(self, args: List[str]) -> None:
        """Print the most recent commands."""
        if not self.inputs.history:
            print("No commands entered yet.")
            return
        for index, line in enumerate(self.inputs.history[-20:], start=1):
            print(f"  {index:>2}: {line}")

    def cmd_help(self, args: List[str]) -> None:
        """Print the command reference."""
        print(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.stop()


def main(argv: Optional[List[str]] = None) -> int:
    """Parse arguments, configure logging and run the application.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None, help="JSON parameter file")
    parser.add_argument("--log-file", default="dispatch.log", help="log file path")
    args = parser.parse_args(argv)
    logging.basicConfig(
        filename=args.log_file,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = DispatchApp(config_path=args.config)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
