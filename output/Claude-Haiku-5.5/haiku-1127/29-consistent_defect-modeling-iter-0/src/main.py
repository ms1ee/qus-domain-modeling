"""Command-line entry point for the food delivery dispatch simulator.

Run with::

    python src/main.py [--debug]
"""

import logging
import math
import sys

try:  # Enables arrow-key history on platforms that provide readline.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

from config import (DEFAULT_STATE_FILE, MAX_TICKS_PER_COMMAND,
                    STATE_NAMES)
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from path_planner import PathPlanner
from system import SystemManager, init_system

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] [s]  Create an order (restaurant then customer, 0-800).
                           Prompts for the four numbers if omitted.
  status [st]              Show funds, pending orders and every rider.
  orders [o]               Show all orders with timing and assignment.
  riders [r]               Show the status-change log of every rider.
  map [m]                  Show the ASCII map with riders and active orders.
  tick [n] [t]             Advance simulated time by n ticks (default 1).
  save [path]              Save the system state as JSON.
  history [hist]           Show previously entered commands.
  help [h, ?]              Show this help.
  quit [q] / exit [x]      Leave the program."""


class DispatchApp:
    """Glue layer that dispatches user commands to the simulation modules."""

    def __init__(self, input_manager: InputManager = None) -> None:
        """Initialise the system state and collaborating managers."""
        init_system()
        self.system = SystemManager()
        self.orders = OrderManager()
        self.planner = PathPlanner()
        self.display = DisplayManager()
        self.input = input_manager or InputManager()
        self._handlers = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "tick": self._cmd_tick,
            "save": self._cmd_save,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
        }

    def run(self) -> None:
        """Run the interactive loop until the system stops running."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.running:
            try:
                line = self.input.read_line("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.running = False
                break
            if not line:
                continue
            try:
                self.dispatch(line)
            except ValueError as exc:
                print(f"Error: {exc}")
            except Exception:  # Error recovery: keep the session alive.
                logger.exception("Unexpected error while handling command")
                print("An unexpected error occurred; system state preserved.")
        print("Goodbye.")

    def dispatch(self, line: str) -> None:
        """Parse ``line`` and invoke the matching command handler."""
        name, args = self.input.parse_command(line)
        self._handlers[name](args)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _cmd_start(self, args: list) -> None:
        """Create an order, recruit if needed, assign it and show the route."""
        if args:
            tokens = args
        else:
            tokens = self.input.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y: "
            ).split()
        coords = self.input.parse_coordinates(tokens)
        order = self.orders.create_order_from_list(coords)

        pending = len(self.orders.pending_orders())
        new_rider = self.system.recruit_if_needed(pending)
        rider = self.orders.assign_order(order)
        if rider is None:
            print("No rider could be assigned; the order remains pending.")
            return

        route = self.planner.route_corners(
            rider.position, [order.res_pos, order.cus_pos])
        distance = self.planner.route_length(route)
        ticks = math.ceil(distance / rider.speed) if rider.speed > 0 else 0
        queued = len(rider.active_orders) - 1

        print(f"Order {order.id} created.")
        print(f"  Restaurant grid point: {order.res_pos}")
        print(f"  Customer grid point:   {order.cus_pos}")
        if new_rider is not None:
            print(f"  New rider added: yes (ID {new_rider.rider_id})")
        else:
            print("  New rider added: no")
        print(f"  Assigned rider: {rider.rider_id} (speed {rider.speed} units/tick)")
        if queued > 0:
            print(f"  Queued behind {queued} active order(s).")
        print(f"  Route distance: {distance} units, estimated time: {ticks} tick(s)")
        print(self.display.render_map(
            riders=[rider], orders=[order], route=route))

    def _cmd_status(self, args: list) -> None:
        """Print funds, pending count and every rider's state."""
        pending = len(self.orders.pending_orders())
        print(self.display.render_status(
            self.system.funds, self.system.riders, pending))

    def _cmd_orders(self, args: list) -> None:
        """Print the table of all orders."""
        print(self.display.render_orders(self.orders.orders))

    def _cmd_riders(self, args: list) -> None:
        """Print the status-change log of every rider."""
        print(self.display.render_rider_logs(self.system.riders))

    def _cmd_map(self, args: list) -> None:
        """Print the ASCII map of riders and active orders."""
        print(self.display.render_map(
            riders=self.system.riders, orders=self.orders.orders))

    def _cmd_tick(self, args: list) -> None:
        """Advance simulated time, moving every rider."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"'{args[0]}' is not a valid tick count.") from None
        if not 1 <= count <= MAX_TICKS_PER_COMMAND:
            raise ValueError(
                f"Tick count must be between 1 and {MAX_TICKS_PER_COMMAND}.")
        for _ in range(count):
            self.system.tick()
        print(f"Simulated time is now {self.system.simulated_time}.")

    def _cmd_save(self, args: list) -> None:
        """Save the system state to a JSON file."""
        path = args[0] if args else DEFAULT_STATE_FILE
        self.system.save_state(path)
        print(f"State saved to {path}.")

    def _cmd_history(self, args: list) -> None:
        """Print previously entered commands."""
        history = self.input.get_history()
        if not history:
            print("No command history yet.")
            return
        for index, entry in enumerate(history, start=1):
            print(f"{index:>4}  {entry}")

    def _cmd_help(self, args: list) -> None:
        """Print the command reference."""
        print(HELP_TEXT)

    def _cmd_quit(self, args: list) -> None:
        """Stop the main loop."""
        self.system.running = False


def main(argv=None) -> int:
    """Configure logging and start the interactive application.

    Args:
        argv: Optional argument list; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    argv = sys.argv[1:] if argv is None else argv
    level = logging.DEBUG if "--debug" in argv else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = DispatchApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
