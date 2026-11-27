"""Command-line entry point for the food delivery dispatch simulator.

Run from the project root with::

    python src/main.py [--config path/to/config.json] [--log-level INFO]
"""

import argparse
import logging
import sys
from typing import Callable, Dict, List, Optional

from display import DisplayManager
from input_manager import InputManager
from path_planner import STEP, PathPlanner
from system import DEFAULT_SAVE_PATH, SystemManager, init_system, load_config

logger = logging.getLogger(__name__)

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order (restaurant, then customer; 0-800).
                       Prompts for the values if omitted.
  status (st)          Show funds, riders and their orders.
  orders (o)           Show all orders with timing and rider data.
  riders (r)           Show every rider status-change record.
  map (m)              Show the ASCII city map.
  tick [n] (t)         Advance the simulation by n ticks (default 1).
  check (c)            Run consistency checks and repair problems.
  save [file]          Save system state to JSON (default dispatch_state.json).
  history              Show command history.
  !!  /  !n            Repeat the last command / history entry n.
  help (h, ?)          Show this help.
  quit (q) / exit (e)  Exit the program."""


class DispatchApp:
    """Interactive command loop tying together the system and the displays.

    Attributes:
        system: The SystemManager being controlled.
        input_manager: Parses commands and keeps history.
        display: Renders status, tables and maps.
        planner: Path planner used to preview routes.
    """

    def __init__(self, system: SystemManager,
                 input_manager: Optional[InputManager] = None,
                 display: Optional[DisplayManager] = None,
                 planner: Optional[PathPlanner] = None) -> None:
        self.system = system
        self.input_manager = input_manager or InputManager()
        self.display = display or DisplayManager()
        self.planner = planner or PathPlanner()
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "tick": self._cmd_tick,
            "check": self._cmd_check,
            "save": self._cmd_save,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
        }

    def run(self) -> None:
        """Run the main command loop until the system stops or input ends."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            self.execute(line)
        print("Goodbye.")

    def execute(self, line: str) -> None:
        """Parse and run one command line, reporting any errors."""
        try:
            command, args = self.input_manager.parse(line)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        if not command:
            return
        handler = self._handlers.get(command)
        if handler is None:
            print(f"Unknown command '{command}'. Type 'help' for the command list.")
            return
        try:
            handler(args)
        except ValueError as exc:
            print(f"Error: {exc}")
        except Exception:
            logger.exception("Unexpected error while running '%s'", command)
            print("Unexpected internal error. The system state was kept; see the log.")

    # ----- command handlers -------------------------------------------
    def _cmd_start(self, args: List[str]) -> None:
        """Create an order, dispatch it and show the route map."""
        if not args:
            raw = input("Enter restaurant_x restaurant_y customer_x customer_y (0-800): ")
            args = raw.split()
        rx, ry, cx, cy = self.input_manager.parse_coordinates(args)

        order = self.system.create_order(rx, ry, cx, cy)
        rider, added = self.system.dispatch_order(order)
        if rider is None:
            self.system.order_manager.reject(order)
            print(f"Order #{order.id} rejected: no rider available and "
                  f"insufficient funds ({self.system.funds}) to recruit one.")
            return

        route_nodes = [rider.position]
        leg_to_restaurant = self.planner.find_path(rider.position, order.restaurant_pos) or []
        leg_to_customer = self.planner.find_path(order.restaurant_pos,
                                                 order.customer_pos) or []
        route_nodes += leg_to_restaurant + leg_to_customer
        total_steps = len(route_nodes) - 1
        total_units = total_steps * STEP
        ticks = self.planner.estimate_ticks(total_steps, rider.speed)

        print(f"Order #{order.id} accepted (tick {order.start_time}).")
        print(f"  Restaurant: input ({rx},{ry}) -> grid {order.restaurant_pos}")
        print(f"  Customer:   input ({cx},{cy}) -> grid {order.customer_pos}")
        print(f"  New rider recruited: {'yes' if added else 'no'}")
        queued = len(rider.orders) > 1
        print(f"  Assigned rider: #{rider.rider_id} at {rider.position}, "
              f"speed {rider.speed} units/tick, orders held {rider.load}"
              + (" (queued behind earlier orders)" if queued else ""))
        print(f"  Route: {total_units} units, estimated {ticks} tick(s)")
        print("Route map:")
        print(self.display.render_map(self.system.riders,
                                      [order], route=route_nodes))

    def _cmd_status(self, args: List[str]) -> None:
        """Show system funds and rider details."""
        print(self.display.render_status(self.system))

    def _cmd_orders(self, args: List[str]) -> None:
        """Show the order table."""
        print(self.display.render_orders(self.system.order_manager.orders))

    def _cmd_riders(self, args: List[str]) -> None:
        """Show the rider status-change log."""
        print(self.display.render_rider_logs(self.system.riders))

    def _cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map with riders and active orders."""
        print(self.display.render_map(self.system.riders,
                                      self.system.order_manager.active_orders()))

    def _cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError("tick count must be an integer") from None
            if not 1 <= count <= 1000:
                raise ValueError("tick count must be between 1 and 1000")
        for _ in range(count):
            self.system.tick()
        print(f"Advanced {count} tick(s). Current tick: {self.system.current_tick}.")

    def _cmd_check(self, args: List[str]) -> None:
        """Run consistency checks and report the outcome."""
        problems = self.system.check_consistency(repair=True)
        if not problems:
            print("System state is consistent.")
            return
        print("Problems found (repaired where possible):")
        for problem in problems:
            print(f"  - {problem}")

    def _cmd_save(self, args: List[str]) -> None:
        """Save the system state to a JSON file."""
        path = args[0] if args else DEFAULT_SAVE_PATH
        try:
            self.system.save(path)
        except OSError as exc:
            print(f"Error: could not save to '{path}': {exc}")
            return
        print(f"State saved to {path}.")

    def _cmd_history(self, args: List[str]) -> None:
        """Print the command history."""
        history = self.input_manager.command_history
        if not history:
            print("No commands yet.")
            return
        for index, entry in enumerate(history, start=1):
            print(f"  {index:>3}  {entry}")

    def _cmd_help(self, args: List[str]) -> None:
        """Print the command reference."""
        print(HELP_TEXT)

    def _cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.is_running = False


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Optional command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="path to a JSON configuration file")
    parser.add_argument("--log-level", default="WARNING",
                        help="logging level (DEBUG, INFO, WARNING, ERROR)")
    args = parser.parse_args(argv)

    level = getattr(logging, args.log_level.upper(), logging.WARNING)
    logging.basicConfig(level=level,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    system = init_system()
    if args.config:
        try:
            system.apply_config(load_config(args.config))
        except (OSError, ValueError) as exc:
            print(f"Warning: could not apply configuration ({exc}). Using defaults.")

    DispatchApp(system).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
