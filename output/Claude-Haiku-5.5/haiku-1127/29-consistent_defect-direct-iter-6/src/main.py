"""Command-line entry point for the food delivery dispatch simulator.

Run with::

    python src/main.py [--config path/to/config.json]

Commands:
    start [rx ry cx cy]   Place an order (prompts if coordinates are omitted).
    status                Show funds and each rider's state and orders.
    orders                Show all orders.
    riders                Show every recorded rider status change.
    map                   Show the ASCII map.
    tick [n]              Advance the simulation by n ticks (default 1).
    history               Show command history.
    help                  Show help.
    quit / exit           Leave the program.
"""

import logging
import math
import sys
from typing import Callable, Dict, List, Optional

import system
from display import DisplayManager
from input_manager import InputManager
from order import OrderError, OrderManager
from path_planner import route_length

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order. Coordinates are integers 0-1000.
                       Without arguments you are prompted for each value.
  status  (s)          Funds, riders, their states and assigned orders.
  orders  (o)          Table of all orders.
  riders  (r)          Status-change history of every rider.
  map     (m)          ASCII map (R rider, S restaurant, C customer, # street).
  tick [n] (t)         Advance the simulation by n ticks (default 1).
  history (hist)       Show command history. '!!' repeats the last command,
                       '!n' repeats history entry n.
  help    (h, ?)       Show this help.
  quit    (q, exit)    Exit the program."""


class DispatchApp:
    """Interactive application wiring the system, orders, display and input."""

    def __init__(self, inputs: Optional[InputManager] = None) -> None:
        """Initialise the system and its collaborators.

        Args:
            inputs: Optional input manager (useful for scripted sessions).
        """
        self.system = system.init_system()
        self.orders = OrderManager(self.system)
        self.display = DisplayManager()
        self.inputs = inputs or InputManager()
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }

    def run(self) -> None:
        """Run the main command loop until the system stops."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.running:
            try:
                command, args = self.inputs.read_command()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            except ValueError as exc:
                print(f"Error: {exc}")
                continue
            if not command:
                continue
            try:
                self._handlers[command](args)
            except ValueError as exc:
                print(f"Error: {exc}")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            except Exception:  # pylint: disable=broad-except
                logger.exception("Unexpected error while running '%s'", command)
                print("Unexpected internal error; system state was preserved. "
                      "See dispatch.log for details.")
        print("Goodbye.")

    def cmd_start(self, args: List[str]) -> None:
        """Place an order and show the assignment and route map."""
        if args:
            values = self.inputs.parse_coordinates(args)
        else:
            values = self.inputs.prompt_coordinates()
        try:
            result = self.orders.submit_order((values[0], values[1]),
                                              (values[2], values[3]))
        except OrderError as exc:
            raise ValueError(str(exc)) from None

        order = result["order"]
        rider = result["rider"]
        route = result["route"]
        length = route_length(route)
        speed = max(1, rider.speed)
        ticks = math.ceil(length / speed)

        print(f"Order #{order.id} accepted.")
        print(f"Restaurant grid point: {order.res_pos}  (input {values[0]}, {values[1]})")
        print(f"Customer grid point:   {order.cus_pos}  (input {values[2]}, {values[3]})")
        if result["new_rider"]:
            print(f"New rider added: yes (rider #{rider.rider_id})")
        else:
            print("New rider added: no")
        print(f"Assigned rider: #{rider.rider_id} at ({rider.x}, {rider.y}), "
              f"status={rider.state_name}, speed={rider.speed} units/tick, "
              f"active orders={len(rider.active_orders())}")
        print(f"Route length: {length} units; estimated time: {ticks} ticks "
              f"(excludes queued orders).")
        print(self.display.render_map(self.system.riders, self.orders.orders, route))

    def cmd_status(self, _args: List[str]) -> None:
        """Print the status snapshot."""
        print(f"Tick: {self.system.tick}")
        print(self.display.render_status(self.system.funds, self.system.riders))

    def cmd_orders(self, _args: List[str]) -> None:
        """Print the order table."""
        print(self.display.render_orders(self.orders.orders))

    def cmd_riders(self, _args: List[str]) -> None:
        """Print rider status-change history."""
        print(self.display.render_rider_history(self.system.riders))

    def cmd_map(self, _args: List[str]) -> None:
        """Print the ASCII map."""
        print(self.display.render_map(self.system.riders, self.orders.orders))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation.

        Args:
            args: Optional tick count.

        Raises:
            ValueError: If the count is not an integer in 1-1000.
        """
        steps = 1
        if args:
            try:
                steps = int(args[0])
            except ValueError:
                raise ValueError(f"Tick count '{args[0]}' is not an integer.") from None
            if not 1 <= steps <= 1000:
                raise ValueError("Tick count must be between 1 and 1000.")
        self.system.advance_tick(steps)
        print(f"Advanced {steps} tick(s); current tick = {self.system.tick}")

    def cmd_history(self, _args: List[str]) -> None:
        """Print the command history."""
        entries = self.inputs.history
        if not entries:
            print("No commands yet.")
            return
        for index, entry in enumerate(entries, start=1):
            print(f"  {index:>3}  {entry}")

    def cmd_help(self, _args: List[str]) -> None:
        """Print help text."""
        print(HELP_TEXT)

    def cmd_quit(self, _args: List[str]) -> None:
        """Stop the main loop."""
        self.system.stop()


def main(argv: Optional[List[str]] = None) -> None:
    """Program entry point.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).
    """
    logging.basicConfig(
        filename="dispatch.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = sys.argv[1:] if argv is None else argv
    if len(args) >= 2 and args[0] == "--config":
        try:
            system.load_config(args[1])
        except (OSError, ValueError) as exc:
            print(f"Warning: could not load configuration ({exc}); using defaults.")
    DispatchApp().run()


if __name__ == "__main__":
    main()
