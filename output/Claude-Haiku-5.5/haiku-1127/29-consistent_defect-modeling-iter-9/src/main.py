"""Command-line entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [config.json] [--debug]
"""

import logging
import sys
from typing import Callable, Dict, List, Optional

from display_manager import DisplayManager
from input_manager import InputError, InputManager
from order_model import STATUS_COMPLETED
from system import SystemManager, init_system

logger = logging.getLogger("dispatch.main")

DEFAULT_STATE_PATH = "dispatch_state.json"

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] (s)  Place an order: restaurant then customer coordinates (0-1000).
                           Simulates until delivered and shows the route map.
  status (st)              System funds, riders, their state and order lists.
  orders (o)               Table of all orders.
  riders (r)               Status-change log of every rider.
  map (m)                  ASCII map with riders and active orders.
  tick [n] (t)             Advance simulated time by n ticks (default 1).
  save [path]              Save state to JSON (default dispatch_state.json).
  history                  Show command history.
  !!                       Repeat the previous command.
  help (h, ?)              Show this help.
  quit / exit (q, x)       Leave the program.
"""


class DispatchApp:
    """Interactive application wiring the system, display and input layers."""

    def __init__(self, config_path: Optional[str] = None,
                 state_path: str = DEFAULT_STATE_PATH) -> None:
        """Create the application.

        Args:
            config_path: Optional JSON configuration file.
            state_path: Default file used by the save command.
        """
        self.system: SystemManager = init_system(config_path)
        self.display = DisplayManager()
        self.inputs = InputManager()
        self.state_path = state_path
        self.handlers: Dict[str, Callable[[List[str]], None]] = {
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
            "exit": self.cmd_quit,
        }

    def run(self) -> None:
        """Run the main loop until the user quits or input ends."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = self.inputs.read_command("dispatch> ")
                if not line:
                    continue
                command, args = InputManager.parse_command(line)
                self.handlers[command](args)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                break
            except InputError as exc:
                print(f"Input error: {exc}")
            except Exception as exc:  # Error recovery: report and continue.
                logger.exception("Unexpected error while handling command")
                print(f"Unexpected error ({exc}); the system state was preserved. Try again.")
        print("Simulator stopped.")

    def cmd_start(self, args: List[str]) -> None:
        """Place an order and simulate it to completion.

        Args:
            args: Optional four coordinate tokens; prompts when omitted.
        """
        if args:
            coords = InputManager.parse_coordinates(args)
        else:
            print("Enter: restaurant_x restaurant_y customer_x customer_y")
            line = self.inputs.read_command("start> ")
            coords = InputManager.parse_coordinates(line.split())
        rx, ry, cx, cy = coords
        result = self.system.submit_order((rx, ry), (cx, cy))
        order = result["order"]
        rider = result["rider"]
        print(f"Restaurant grid point: {order.restaurant_pos}")
        print(f"Customer grid point:   {order.customer_pos}")
        print(f"New rider recruited:   {'yes' if result['recruited'] else 'no'}")
        if rider is None:
            print("No rider available. The order is pending and will be dispatched "
                  "when a rider can be recruited.")
            return
        print(f"Assigned to rider #{rider.rider_id} (speed {rider.speed} units/tick)")
        ticks = self.system.run_until_complete(order)
        if order.status == STATUS_COMPLETED:
            print(f"Delivered in {order.time_taken} ticks.")
        else:
            print(f"Order not completed within the tick limit ({ticks} ticks simulated).")
        print(self.display.format_route_report(order, rider, ticks))
        print(self.display.render_map(riders=[rider], orders=[order], route=order.route))

    def cmd_status(self, args: List[str]) -> None:
        """Print the system snapshot and any consistency problems."""
        print(self.display.format_status(self.system.funds, self.system.current_tick,
                                         self.system.riders))
        issues = self.system.check_consistency()
        if issues:
            print("Consistency warnings:")
            for issue in issues:
                print(f"  - {issue}")

    def cmd_orders(self, args: List[str]) -> None:
        """Print the table of all orders."""
        print(self.display.format_orders(self.system.order_manager.orders))

    def cmd_riders(self, args: List[str]) -> None:
        """Print the status-change log of every rider."""
        print(self.display.format_rider_log(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map with riders and active orders."""
        active = [o for o in self.system.order_manager.orders if o.status != STATUS_COMPLETED]
        print(self.display.render_map(riders=self.system.riders, orders=active))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation by one or more ticks.

        Args:
            args: Optional tick count between 1 and 1000.
        """
        count = InputManager.parse_positive_int(args, default=1, low=1, high=1000)
        for _ in range(count):
            self.system.tick()
        print(f"Advanced {count} tick(s); current tick is {self.system.current_tick}.")

    def cmd_save(self, args: List[str]) -> None:
        """Save the system state to a JSON file.

        Args:
            args: Optional file path.
        """
        path = args[0] if args else self.state_path
        try:
            self.system.save_state(path)
        except OSError as exc:
            print(f"Could not save state to {path}: {exc}")
            return
        print(f"State saved to {path}.")

    def cmd_history(self, args: List[str]) -> None:
        """Print the command history."""
        if not self.inputs.command_history:
            print("No commands yet.")
            return
        for index, command in enumerate(self.inputs.command_history, start=1):
            print(f"  {index:>3}: {command}")

    def cmd_help(self, args: List[str]) -> None:
        """Print the command help text."""
        print(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.is_running = False


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        Process exit code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    level = logging.WARNING
    if "--debug" in args:
        level = logging.DEBUG
        args.remove("--debug")
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config_path = args[0] if args else None
    app = DispatchApp(config_path=config_path)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
