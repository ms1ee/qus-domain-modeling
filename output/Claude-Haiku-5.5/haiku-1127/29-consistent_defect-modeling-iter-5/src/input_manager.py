"""Command-line interaction: parsing, validation, command dispatch and the main loop."""

import logging
import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from display import DisplayManager
from order import OrderManager
from order_model import COORD_MAX, COORD_MIN
from path_planner import PathPlanner
from system import SystemManager

logger = logging.getLogger(__name__)

MAX_TICKS_PER_COMMAND = 10000


class InputManager:
    """Parses user commands and drives the simulator.

    Attributes:
        command_history: Every accepted command line, in order.
    """

    ALIASES = {
        "s": "start",
        "st": "status",
        "o": "orders",
        "r": "riders",
        "m": "map",
        "t": "tick",
        "h": "help",
        "?": "help",
        "hist": "history",
        "q": "quit",
        "x": "exit",
    }

    HELP_TEXT = (
        "Commands:\n"
        "  start [rx ry cx cy]  create an order (restaurant, customer); prompts if omitted\n"
        "  status               funds, riders and their orders\n"
        "  orders               details of all orders\n"
        "  riders               status-change log of all riders\n"
        "  map                  ASCII map of riders and orders\n"
        "  tick [n]             advance the simulation by n ticks (default 1)\n"
        "  history              list previous commands\n"
        "  !!                   repeat the last command\n"
        "  help / ?             show this help\n"
        "  quit / exit          leave the program\n"
        "Shortcuts: s, st, o, r, m, t, h, ?, hist, q, x"
    )

    def __init__(self, input_func: Optional[Callable[[str], str]] = None,
                 output_func: Optional[Callable[[str], None]] = None) -> None:
        """Create the input manager and wire up collaborators.

        Args:
            input_func: Function used to read a line (defaults to ``input``).
            output_func: Function used to print text (defaults to ``print``).
        """
        self.command_history: List[str] = []
        self.input_func = input_func or input
        self.output = output_func or print
        self.order_manager = OrderManager()
        self.system = SystemManager()
        self.display = DisplayManager()
        self.planner = PathPlanner()
        self._handlers: Dict[str, Callable[[Sequence[str]], None]] = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "history": self.cmd_history,
            "help": self.cmd_help,
        }

    @staticmethod
    def parse_command(text: str) -> Tuple[str, List[str]]:
        """Split a command line into a normalized name and its arguments.

        Args:
            text: Raw command line.

        Returns:
            (command_name, arguments). The name is "" for blank input.
        """
        tokens = text.split()
        if not tokens:
            return "", []
        name = tokens[0].lower()
        return InputManager.ALIASES.get(name, name), tokens[1:]

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Validate four coordinate tokens.

        Args:
            tokens: Raw string tokens, expected [rx, ry, cx, cy].

        Returns:
            List of four integers.

        Raises:
            ValueError: If the count is wrong, a token is not an integer, or a
                value is outside 0-1000.
        """
        if len(tokens) != 4:
            raise ValueError(
                f"Expected 4 integers (restaurant x y, customer x y), got {len(tokens)}."
            )
        values: List[int] = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise ValueError(f"'{token}' is not an integer.") from None
            if not COORD_MIN <= value <= COORD_MAX:
                raise ValueError(
                    f"Coordinate {value} is out of range {COORD_MIN}-{COORD_MAX}."
                )
            values.append(value)
        return values

    def handle(self, line: str) -> bool:
        """Process a single command line.

        Args:
            line: Raw input line.

        Returns:
            False if the program should exit, True otherwise.
        """
        text = line.strip()
        if not text:
            return True
        if text == "!!":
            if not self.command_history:
                self.output("No previous command to repeat.")
                return True
            text = self.command_history[-1]
            self.output(f"Repeating: {text}")
        self.command_history.append(text)

        name, args = self.parse_command(text)
        if name in ("quit", "exit"):
            self.output("Goodbye.")
            return False
        handler = self._handlers.get(name)
        if handler is None:
            self.output(f"Unknown command '{name}'. Type 'help' for a list of commands.")
            return True
        try:
            handler(args)
        except ValueError as exc:
            self.output(f"Input error: {exc}")
        return True

    def run(self) -> None:
        """Run the interactive command loop until quit or end of input."""
        self.output("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = self.input_func("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self.output("")
                break
            try:
                keep_running = self.handle(line)
            except Exception:  # noqa: BLE001 - recover from unexpected errors
                logger.exception("Unexpected error while handling command")
                self.output("An unexpected error occurred; the system state was preserved.")
                keep_running = True
            if not keep_running:
                break
        self.system.stop()

    def _prompt(self, message: str) -> str:
        """Prompt the user for input.

        Args:
            message: Prompt text.

        Returns:
            The entered line.
        """
        return self.input_func(message)

    def cmd_start(self, args: Sequence[str]) -> None:
        """Create an order, assign it and show the route to the rider.

        Args:
            args: Optional four coordinates; prompted for when omitted.
        """
        raw = list(args) if args else self._prompt(
            "Enter restaurant_x restaurant_y customer_x customer_y: ").split()
        rx, ry, cx, cy = self.parse_coordinates(raw)
        result = self.order_manager.submit_order(rx, ry, cx, cy)
        order = result["order"]
        rider = result["rider"]
        new_riders = result["new_riders"]

        self.output(f"Order #{order.id} created at tick {order.start_time}.")
        self.output(f"Restaurant grid position: {order.restaurant_pos}")
        self.output(f"Customer grid position: {order.customer_pos}")
        if new_riders:
            ids = ", ".join(f"#{r.rider_id}" for r in new_riders)
            self.output(f"New rider added: yes ({ids}); funds now {self.system.funds}")
        else:
            self.output("New rider added: no")

        if rider is None:
            self.output("No rider could be assigned; the order stays pending.")
            return

        route = self.planner.plan_multi_route(
            [rider.position, order.restaurant_pos, order.customer_pos])
        length = PathPlanner.route_length(route)
        ticks = math.ceil(length / rider.speed) if rider.speed > 0 else -1
        self.output(f"Assigned to Rider #{rider.rider_id} (speed {rider.speed} units/tick).")
        self.output(f"Route length: {length} units; estimated time: {ticks} ticks.")
        self.output(self.display.render_map(self.system.riders, self.system.orders, route))

    def cmd_status(self, args: Sequence[str]) -> None:
        """Show system funds, riders and their order lists.

        Args:
            args: Ignored.
        """
        self.output(self.display.render_status(
            self.system.funds, self.system.time, self.system.riders))

    def cmd_orders(self, args: Sequence[str]) -> None:
        """Show details of all orders.

        Args:
            args: Ignored.
        """
        self.output(self.display.render_orders(self.system.orders))

    def cmd_riders(self, args: Sequence[str]) -> None:
        """Show the status-change history of all riders.

        Args:
            args: Ignored.
        """
        self.output(self.display.render_rider_logs(self.system.riders))

    def cmd_map(self, args: Sequence[str]) -> None:
        """Show the ASCII map with riders and active orders.

        Args:
            args: Ignored.
        """
        self.output(self.display.render_map(self.system.riders, self.system.orders))

    def cmd_tick(self, args: Sequence[str]) -> None:
        """Advance the simulation.

        Args:
            args: Optional number of ticks (1 to 10000).

        Raises:
            ValueError: If the count is not a valid positive integer.
        """
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"'{args[0]}' is not an integer.") from None
            if not 1 <= count <= MAX_TICKS_PER_COMMAND:
                raise ValueError(f"Tick count must be between 1 and {MAX_TICKS_PER_COMMAND}.")
        for _ in range(count):
            self.system.tick()
            assigned, new_riders = self.order_manager.dispatch_pending()
            for order, rider in assigned:
                self.output(f"Tick {self.system.time}: order #{order.id} assigned to rider #{rider.rider_id}.")
            for rider in new_riders:
                self.output(f"Tick {self.system.time}: rider #{rider.rider_id} recruited.")
        self.output(f"Time is now tick {self.system.time}. Funds: {self.system.funds}.")

    def cmd_history(self, args: Sequence[str]) -> None:
        """List previously entered commands.

        Args:
            args: Ignored.
        """
        if not self.command_history:
            self.output("(no history)")
            return
        for index, command in enumerate(self.command_history, start=1):
            self.output(f"{index:>4}  {command}")

    def cmd_help(self, args: Sequence[str]) -> None:
        """Show the command list.

        Args:
            args: Ignored.
        """
        self.output(self.HELP_TEXT)
