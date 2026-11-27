"""Command parsing, validation, and the interactive command loop."""

import logging
import math
from typing import Any, Callable, Dict, List, Optional, Sequence

from display import DisplayManager
from globalvar import get_value
from grid_map import MAP_SIZE
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

COMMAND_ALIASES: Dict[str, str] = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "q": "quit",
    "exit": "quit",
}

HELP_TEXT = """\
Commands (shortcut in brackets):
  start [rx ry cx cy]  (s)   Place an order: restaurant then customer
                             coordinates (0-800). Prompts if omitted.
  status               (st)  Funds, riders, and per-rider details.
  orders               (o)   All order details.
  riders               (r)   Rider status-change event log.
  map                  (m)   ASCII map with riders and active orders.
  tick [n]             (t)   Advance simulated time by n ticks (default 1).
  save [file]                Save a JSON snapshot of the system.
  history                    Show previously entered commands.
  !!  /  !n                  Repeat the last command / history entry n.
  help                 (h)   Show this help.
  quit                 (q)   Exit the program (also: exit).
"""


class InputManager:
    """Parses and executes user commands.

    Attributes:
        system (SystemManager): The system being controlled.
        display (DisplayManager): Renderer for tables and maps.
        commandHistory (list[str]): Commands entered so far.
    """

    def __init__(self, system, display: Optional[DisplayManager] = None,
                 input_func: Optional[Callable[[str], str]] = None,
                 output_func: Optional[Callable[..., Any]] = None):
        """Create the input manager.

        Args:
            system (SystemManager): The system to control.
            display (DisplayManager | None): Renderer instance.
            input_func (callable | None): Function used to read input.
            output_func (callable | None): Function used to print output.
        """
        self.system = system
        self.display = display or DisplayManager()
        self.commandHistory: List[str] = []
        self._input = input_func or input
        self._output = output_func or print
        self._planner = PathPlanner()
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
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

    def _print(self, text: str = "") -> None:
        """Print text through the configured output function."""
        self._output(text)

    def run(self) -> None:
        """Run the interactive loop until the system stops."""
        self._print("Food delivery dispatch simulator. Type 'help' for "
                    "commands.")
        while self.system.isRunning:
            try:
                line = self._input("dispatch> ")
            except EOFError:
                self._print()
                self.system.stop()
                break
            except KeyboardInterrupt:
                self._print("\nUse 'quit' to exit.")
                continue
            self.process_line(line)

    def process_line(self, line: str) -> None:
        """Expand shortcuts, record history, and dispatch one command.

        Args:
            line (str): Raw user input.
        """
        line = (line or "").strip()
        if not line:
            return
        try:
            if line == "!!":
                if not self.commandHistory:
                    self._print("No previous command to repeat.")
                    return
                line = self.commandHistory[-1]
            elif line.startswith("!") and line[1:].isdigit():
                index = int(line[1:])
                if not 1 <= index <= len(self.commandHistory):
                    self._print(f"No history entry {index}.")
                    return
                line = self.commandHistory[index - 1]
            self.commandHistory.append(line)
            tokens = line.split()
            name = tokens[0].lower()
            name = COMMAND_ALIASES.get(name, name)
            handler = self._handlers.get(name)
            if handler is None:
                self._print(f"Unknown command '{tokens[0]}'. "
                            f"Type 'help' for the command list.")
                return
            handler(tokens[1:])
        except ValueError as exc:
            self._print(f"Invalid input: {exc}")
        except RuntimeError as exc:
            self._print(f"Error: {exc}")
        except EOFError:
            self._print()
            self.system.stop()
        except Exception:  # noqa: BLE001 - keep the session alive
            logger.exception("Unexpected error while running command.")
            self._print("An unexpected error occurred; system state was "
                        "preserved. See the log for details.")

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Validate that tokens are integers within the map range.

        Args:
            tokens (sequence[str]): Raw coordinate strings.

        Returns:
            list[int]: Parsed integer coordinates.

        Raises:
            ValueError: If a token is not an integer or is out of range.
        """
        values = []
        for token in tokens:
            try:
                value = int(token)
            except (TypeError, ValueError):
                raise ValueError(f"'{token}' is not an integer.")
            if not 0 <= value <= MAP_SIZE:
                raise ValueError(f"coordinate {value} is out of range "
                                 f"0-{MAP_SIZE}.")
            values.append(value)
        return values

    def _prompt_coordinates(self) -> Optional[List[int]]:
        """Interactively ask for the four order coordinates.

        Returns:
            list[int] | None: The four coordinates, or None if cancelled.
        """
        labels = ["restaurant x", "restaurant y", "customer x", "customer y"]
        values: List[int] = []
        for label in labels:
            while True:
                raw = self._input(
                    f"  {label} (0-{MAP_SIZE}, 'cancel' to abort): ").strip()
                if raw.lower() == "cancel":
                    return None
                try:
                    values.extend(self.parse_coordinates([raw]))
                except ValueError as exc:
                    self._print(f"  Invalid: {exc}")
                    continue
                break
        return values

    def _projected_route(self, rider, order) -> List[tuple]:
        """Build the route from the rider's position through the order.

        Args:
            rider (Rider): Assigned rider.
            order (Order): The new order.

        Returns:
            list[tuple[int, int]]: Route points starting at the rider.
        """
        to_restaurant = self._planner.plan(rider.position, order.res_pos)
        to_customer = self._planner.plan(order.res_pos, order.cus_pos)
        return [rider.position] + to_restaurant + to_customer

    def cmd_start(self, args: List[str]) -> None:
        """Place a new order and show the assignment and route.

        Args:
            args (list[str]): Either empty (interactive prompts) or four
                integers: restaurant x, y and customer x, y.

        Raises:
            ValueError: If the arguments are malformed.
        """
        if args:
            if len(args) != 4:
                raise ValueError("start needs four integers: restaurant_x "
                                 "restaurant_y customer_x customer_y.")
            values = self.parse_coordinates(args)
        else:
            values = self._prompt_coordinates()
            if values is None:
                self._print("Order entry cancelled.")
                return
        restaurant = (values[0], values[1])
        customer = (values[2], values[3])
        cost = self.system.recruitmentCost
        order, rider, new_rider = self.system.dispatch_order(restaurant,
                                                             customer)
        self._print(f"Restaurant grid position: {order.res_pos} | "
                    f"Customer grid position: {order.cus_pos} | "
                    f"Order #{order.id}")
        if new_rider:
            self._print(f"New rider R{rider.rider_id} recruited (cost {cost}, "
                        f"funds left {self.system.funds}).")
        else:
            self._print(f"Assigned to existing rider R{rider.rider_id} "
                        f"(now carrying {len(rider.orders)} order(s)).")
        route = self._projected_route(rider, order)
        length = PathPlanner.route_length(route[0], route[1:])
        eta = math.ceil(length / rider.speed) if length else 0
        self._print(f"Rider R{rider.rider_id}: position {rider.position}, "
                    f"speed {rider.speed} units/tick.")
        self._print(f"Projected route: {length} units, about {eta} tick(s).")
        if len(rider.orders) > 1:
            self._print("Note: the rider has other queued orders; the route "
                        "and ETA above ignore them.")
        self._print(self.display.render_map(riders=[rider],
                                            orders=[order], route=route))

    def cmd_status(self, args: List[str]) -> None:
        """Show system funds, riders, and their states.

        Args:
            args (list[str]): Unused.
        """
        self._print(self.display.format_status(self.system))

    def cmd_orders(self, args: List[str]) -> None:
        """Show details for all orders.

        Args:
            args (list[str]): Unused.
        """
        self._print(self.display.format_orders(
            get_value("orders", []) or []))

    def cmd_riders(self, args: List[str]) -> None:
        """Show the rider status-change event log.

        Args:
            args (list[str]): Unused.
        """
        self._print(self.display.format_rider_logs(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map with riders and active orders.

        Args:
            args (list[str]): Unused.
        """
        active = [o for o in get_value("orders", []) if o.is_active]
        self._print(self.display.render_map(riders=self.system.riders,
                                            orders=active))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance simulated time.

        Args:
            args (list[str]): Optional number of ticks.

        Raises:
            ValueError: If the count is not a positive integer within the
                configured limit.
        """
        steps = 1
        if args:
            steps = self.parse_coordinates(args[:1]) and int(args[0])
            limit = int(self.system.config.get("max_ticks_per_command", 1000))
            if steps < 1 or steps > limit:
                raise ValueError(f"tick count must be between 1 and {limit}.")
        self.system.tick(steps)
        active = [o for o in get_value("orders", []) if o.is_active]
        completed = len(get_value("order_history", []))
        self._print(f"Advanced {steps} tick(s). Now at tick "
                    f"{self.system.currentTick}. Active orders: {len(active)}, "
                    f"completed: {completed}.")

    def cmd_save(self, args: List[str]) -> None:
        """Save a JSON snapshot of the system.

        Args:
            args (list[str]): Optional destination file path.
        """
        try:
            path = self.system.save_state(args[0] if args else None)
            self._print(f"System state saved to {path}.")
        except OSError as exc:
            self._print(f"Could not save state: {exc}")

    def cmd_history(self, args: List[str]) -> None:
        """List previously entered commands.

        Args:
            args (list[str]): Unused.
        """
        if not self.commandHistory:
            self._print("No commands entered yet.")
            return
        for index, command in enumerate(self.commandHistory, start=1):
            self._print(f"{index:>4}  {command}")

    def cmd_help(self, args: List[str]) -> None:
        """Print the command reference.

        Args:
            args (list[str]): Unused.
        """
        self._print(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Terminate the program.

        Args:
            args (list[str]): Unused.
        """
        self.system.stop()
        self._print("Goodbye.")
