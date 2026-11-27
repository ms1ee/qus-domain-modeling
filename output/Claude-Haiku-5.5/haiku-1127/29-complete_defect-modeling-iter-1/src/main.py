"""Command-line entry point for the food delivery dispatch simulator."""

import logging
import os
import sys
from typing import List

import globalvar
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager, find_best_rider_for_order
from system import SystemManager, init_system, load_config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DEFAULT_SAVE_PATH = "dispatch_state.json"
LOG_PATH = "dispatch.log"
LOGGER = logging.getLogger("dispatch")

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy]  (n)  Place an order: restaurant then customer grid coords (0-800).
                            Runs the simulation until the order is delivered.
  status               (s)  System funds, time, and every rider's state and orders.
  orders               (o)  Table of all orders with timing, distance and rider.
  riders               (r)  Detailed rider info and every logged status change.
  map                  (m)  ASCII map with riders and active orders.
  tick [n]             (t)  Advance the simulation by n ticks (default 1).
  save [path]               Save system state to JSON (default dispatch_state.json).
  history              List previously entered commands.
  !!                        Repeat the last command.
  help                 (h)  Show this help.
  quit / exit          (q)  Leave the simulator.
"""


class Simulator:
    """Wires the managers together and runs the interactive command loop."""

    def __init__(self, config_path: str = CONFIG_PATH) -> None:
        """Initialize the system state, load configuration and build managers.

        Args:
            config_path: Optional JSON configuration file path.
        """
        init_system()
        self.applied_config = {}
        if os.path.exists(config_path):
            try:
                self.applied_config = load_config(config_path)
            except (OSError, ValueError) as exc:
                print(f"Warning: could not load configuration ({exc}); using defaults.")
        self.system = SystemManager()
        self.orders = OrderManager()
        self.display = DisplayManager()
        self.inputs = InputManager()
        self.handlers = {
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

    def run(self) -> None:
        """Run the interactive loop until quit or end of input."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands.")
        while self.system.running:
            try:
                raw = self.inputs.read_line("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            try:
                self.execute(raw)
            except ValueError as exc:
                print(f"Error: {exc}")
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("unexpected failure while executing %r", raw)
                print("Unexpected internal error; system state preserved. See dispatch.log.")
        self.system.stop()

    def execute(self, raw: str) -> None:
        """Expand, parse and dispatch one command line.

        Args:
            raw: Raw user input.

        Raises:
            ValueError: For invalid input that the user must correct.
        """
        line = self.inputs.expand(raw)
        command, args = self.inputs.parse(line)
        if not command:
            return
        self.inputs.record(line)
        self.handlers[command](args)

    def _riders(self):
        """Return the current rider list."""
        return self.system.riders

    def cmd_start(self, args: List[str]) -> None:
        """Place an order, assign the nearest rider and simulate until delivery.

        Args:
            args: Optional four coordinate tokens; prompted when absent.
        """
        if not args:
            args = self.inputs.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y: "
            ).split()
        res_x, res_y, cus_x, cus_y = self.inputs.parse_coordinates(args)

        order = self.orders.create_order(res_x, res_y, cus_x, cus_y)
        self.system.add_funds(int(globalvar.get_value("order_fee", 100)))

        riders_before = len(self._riders())
        self.system.check_recruitment()
        if not self._riders():
            self.system.recruit_rider()

        rider = find_best_rider_for_order(order)
        if rider is None:
            raise ValueError("no rider is available to take this order")
        order.assign_to(rider.rider_id)

        print(f"Order #{order.id} accepted.")
        print(f"Restaurant grid point : {order.res_pos}")
        print(f"Customer grid point   : {order.cus_pos}")

        max_ticks = int(globalvar.get_value("max_ticks", 10000))
        ticks = 0
        while order.status != "completed":
            if ticks >= max_ticks:
                print(f"Error: order #{order.id} not delivered within {max_ticks} ticks.")
                break
            self.system.tick()
            ticks += 1

        added = len(self._riders()) - riders_before
        if added > 0:
            new_ids = ", ".join(f"#{r.rider_id}" for r in self._riders()[riders_before:])
            print(f"New rider added       : yes ({new_ids})")
        else:
            print("New rider added       : no")
        print(f"Assigned rider        : #{rider.rider_id} (speed {rider.speed} units/tick)")
        print(f"Distance travelled    : {order.distance:.0f} units")
        print(f"Time taken            : {order.time_taken} ticks")
        print("Route map:")
        print(
            self.display.render_map(
                riders=[rider], orders=[order], routes=[order.route]
            )
        )

    def cmd_status(self, args: List[str]) -> None:
        """Print the system snapshot.

        Args:
            args: Ignored.
        """
        print(
            self.display.status_text(
                self.system.funds,
                int(globalvar.get_value("simulated_time", 0)),
                self._riders(),
                self.orders.active_orders(),
            )
        )

    def cmd_orders(self, args: List[str]) -> None:
        """Print the table of all orders.

        Args:
            args: Ignored.
        """
        print(self.display.orders_text(self.orders.all_orders()))

    def cmd_riders(self, args: List[str]) -> None:
        """Print every rider with its full status-change log.

        Args:
            args: Ignored.
        """
        print(self.display.riders_text(self._riders()))

    def cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map of riders and active orders.

        Args:
            args: Ignored.
        """
        active = self.orders.active_orders()
        print(
            self.display.render_map(
                riders=self._riders(),
                orders=active,
                routes=[order.route for order in active],
            )
        )

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation by one or more ticks.

        Args:
            args: Optional tick count (1-1000).

        Raises:
            ValueError: If the count is not an integer in range.
        """
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError as exc:
                raise ValueError(f"tick count '{args[0]}' is not an integer") from exc
            if not 1 <= count <= 1000:
                raise ValueError("tick count must be between 1 and 1000")
        recruited = []
        for _ in range(count):
            new_rider = self.system.tick()
            if new_rider is not None:
                recruited.append(new_rider.rider_id)
        print(f"Advanced {count} tick(s). Simulated time: {globalvar.get_value('simulated_time')}.")
        if recruited:
            print("Recruited rider(s): " + ", ".join(f"#{rid}" for rid in recruited))

    def cmd_save(self, args: List[str]) -> None:
        """Save the system state to a JSON file.

        Args:
            args: Optional output path.

        Raises:
            ValueError: If the file cannot be written.
        """
        path = args[0] if args else DEFAULT_SAVE_PATH
        try:
            self.system.save_state(path)
        except OSError as exc:
            raise ValueError(f"could not save state to {path}: {exc}") from exc
        print(f"State saved to {path}.")

    def cmd_history(self, args: List[str]) -> None:
        """Print the command history.

        Args:
            args: Ignored.
        """
        if not self.inputs.command_history:
            print("No commands entered yet.")
            return
        for index, line in enumerate(self.inputs.command_history, start=1):
            print(f"{index:>4}  {line}")

    def cmd_help(self, args: List[str]) -> None:
        """Print the help text.

        Args:
            args: Ignored.
        """
        print(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop.

        Args:
            args: Ignored.
        """
        self.system.stop()
        print("Goodbye.")


def main() -> int:
    """Configure logging and run the simulator.

    Returns:
        Process exit code.
    """
    try:
        logging.basicConfig(
            filename=LOG_PATH,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    except OSError:
        logging.basicConfig(level=logging.WARNING)
    simulator = Simulator()
    simulator.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
