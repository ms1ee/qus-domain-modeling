"""Command-line entry point for the food delivery dispatch simulator.

Each iteration of the main loop is one simulation tick. The user may enter
commands; after each one the simulation advances by one tick.
"""

import argparse
import logging
import sys
from typing import Callable, Dict, List, Optional

from display_manager import DisplayManager
from globalvar import get_value
from input_manager import InputManager, ValidationError
from order import NoRiderAvailableError
from system import SystemManager, init_system

CONFIG_PATH = "dispatch_config.json"
STATE_PATH = "dispatch_state.json"
LOG_PATH = "dispatch.log"

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy]  (a) Place an order: restaurant then customer, 0-800 each
  status               (s) Show system funds, riders, and their orders
  orders               (o) Show all orders with timing and assignment
  riders               (r) Show every rider status change and event
  map                  (m) Show the ASCII street map with riders and orders
  wait [n]             (w) Advance the simulation by n ticks (default 1)
  history              Show the commands entered this session
  help                 (h) Show this help
  quit / exit          (q) Save state and exit

Every command line is one simulation tick. Press Enter on an empty line to
advance one tick without any other action."""


def configure_logging() -> None:
    """Send log output to the log file so it does not clutter the terminal."""
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


class DispatchApp:
    """Runs the interactive command loop.

    Attributes:
        sysmgr: The system manager.
        display: Output formatter.
        inputs: Input reader and parser.
    """

    def __init__(self, sysmgr: SystemManager, display: DisplayManager, inputs: InputManager) -> None:
        """Create the application.

        Args:
            sysmgr: Initialised system manager.
            display: Display manager for output formatting.
            inputs: Input manager for reading commands.
        """
        self.sysmgr = sysmgr
        self.display = display
        self.inputs = inputs
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "wait": self.cmd_wait,
            "history": self.cmd_history,
            "help": self.cmd_help,
        }

    def run(self) -> None:
        """Run the main loop until the user quits or input closes."""
        print("Food delivery dispatch simulator. Type 'help' for commands.")
        while get_value("running", True):
            try:
                line = self.inputs.read_line(f"[t={self.sysmgr.tick_count}] dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                self.sysmgr.stop()
                break

            try:
                parsed = InputManager.parse_command(line)
            except ValidationError as exc:
                print(f"Error: {exc}")
                parsed = None

            if parsed is not None:
                command, args = parsed
                if command == "quit":
                    self.sysmgr.stop()
                    break
                self._execute(command, args)

            if get_value("running", True):
                self.sysmgr.tick()

    def _execute(self, command: str, args: List[str]) -> None:
        """Run a command handler and convert failures into user messages.

        Args:
            command: Canonical command name.
            args: Arguments following the command.
        """
        handler = self._handlers.get(command)
        if handler is None:
            print(f"Error: command '{command}' is not implemented.")
            return
        try:
            handler(args)
        except (ValidationError, ValueError) as exc:
            print(f"Error: {exc}")
        except NoRiderAvailableError as exc:
            print(f"Order could not be assigned: {exc}")
        except Exception:  # error recovery: log, repair state, keep running
            logging.getLogger(__name__).exception("Command '%s' failed", command)
            print("An internal error occurred. System state was checked and repaired where possible.")
            for issue in self.sysmgr.check_consistency():
                print(f"  repaired: {issue}")

    def cmd_start(self, args: List[str]) -> None:
        """Place an order, assign a rider, and show the route map.

        Args:
            args: Optional four coordinates. If omitted the user is prompted.
        """
        coords = self.inputs.read_order_coordinates(args)
        if coords is None:
            print("Order cancelled.")
            return

        result = self.sysmgr.submit_order(coords)
        order = result["order"]
        rider = result["rider"]
        route = result["route"]
        config = self.sysmgr.config

        from path_planner import grid_cell  # local import keeps top-level imports short

        res_cell = grid_cell(order.res_pos)
        cus_cell = grid_cell(order.cus_pos)
        print(f"Order #{order.id} created at tick {order.start_time}.")
        print(
            f"  Restaurant: ({order.res_pos[0]}, {order.res_pos[1]}) "
            f"grid cell {res_cell}"
        )
        print(
            f"  Customer:   ({order.cus_pos[0]}, {order.cus_pos[1]}) "
            f"grid cell {cus_cell}"
        )
        if result["new_rider"]:
            print(
                f"New rider #{rider.rider_id} recruited "
                f"(cost {config.get('recruit_cost', 0)}); funds now {self.sysmgr.funds}."
            )
        print(
            f"Assigned to rider #{rider.rider_id} at ({rider.x}, {rider.y}), "
            f"speed {rider.speed} units/tick, orders ahead: {result['queued_ahead']}."
        )
        print(
            f"Route: pickup {route['pickup_distance']} units, delivery "
            f"{route['delivery_distance']} units, estimated {route['eta_ticks']} ticks "
            f"(excludes queued orders)."
        )
        print(self.display.render_map(self.sysmgr.riders, get_value("orders", []), route["points"]))

    def cmd_status(self, args: List[str]) -> None:
        """Show funds, rider states, and order lists.

        Args:
            args: Unused.
        """
        config = self.sysmgr.config
        print(
            self.display.format_status(
                self.sysmgr.funds,
                self.sysmgr.riders,
                self.sysmgr.tick_count,
                int(config.get("max_riders", 10)),
            )
        )
        for issue in self.sysmgr.check_consistency():
            print(f"  repaired: {issue}")

    def cmd_orders(self, args: List[str]) -> None:
        """Show details of every order.

        Args:
            args: Unused.
        """
        print(self.display.format_orders(get_value("orders", [])))

    def cmd_riders(self, args: List[str]) -> None:
        """Show the full status change history of every rider.

        Args:
            args: Unused.
        """
        print(self.display.format_rider_history(self.sysmgr.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map with riders and active orders.

        Args:
            args: Unused.
        """
        print(self.display.render_map(self.sysmgr.riders, get_value("orders", [])))

    def cmd_wait(self, args: List[str]) -> None:
        """Advance the simulation by several ticks.

        The main loop already ticks once after each command, so this command
        performs ``n - 1`` additional ticks.

        Args:
            args: Optional tick count.
        """
        ticks = InputManager.parse_wait_ticks(args)
        for _ in range(ticks - 1):
            self.sysmgr.tick()
        print(f"Advanced {ticks} tick(s).")

    def cmd_history(self, args: List[str]) -> None:
        """Print the commands entered in this session.

        Args:
            args: Unused.
        """
        if not self.inputs.history:
            print("No commands entered yet.")
            return
        for index, entry in enumerate(self.inputs.history, start=1):
            print(f"{index:>4}  {entry}")

    def cmd_help(self, args: List[str]) -> None:
        """Print the help text.

        Args:
            args: Unused.
        """
        print(HELP_TEXT)


def main(argv: Optional[List[str]] = None) -> int:
    """Parse arguments, initialise the system, run the loop, and save state.

    Args:
        argv: Optional argument list; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=CONFIG_PATH, help="JSON configuration file")
    parser.add_argument("--state", default=STATE_PATH, help="file to save state to on exit")
    options = parser.parse_args(argv)

    configure_logging()
    sysmgr = init_system(options.config)
    app = DispatchApp(sysmgr, DisplayManager(), InputManager())
    try:
        app.run()
    finally:
        try:
            sysmgr.save_state(options.state)
            print(f"State saved to {options.state}. Goodbye.")
        except OSError as exc:
            logging.getLogger(__name__).error("Could not save state: %s", exc)
            print(f"Warning: could not save state: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
