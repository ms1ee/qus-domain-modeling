"""Command parsing, input validation and the interactive command loop."""

import logging
import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from display import DisplayManager
from path_planner import MAP_SIZE, PathPlanner, path_length
from rider import STATE_NAMES

logger = logging.getLogger(__name__)

BANNER = (
    "=== Food Delivery Order Dispatch Simulator ===\n"
    "Type 'help' for commands, 'quit' to exit."
)

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant x y, customer x y, 0-800).
                       Without arguments you are prompted for the four values.
                       The route is shown and the delivery is simulated.
  status  (s, st)      Show system funds, riders and their orders.
  orders  (o)          Show all orders with time, distance and rider.
  riders  (r)          Show every recorded rider status change.
  map     (m)          Show the ASCII map with riders and active orders.
  tick [n] (t)         Advance the simulation by n ticks (default 1).
  history (hist)       Show command history.
  !!                   Repeat the previous command.
  help    (h, ?)       Show this help.
  quit    (q, exit)    Exit the program.
Coordinates are integers in the range 0-800 and may be separated by spaces
or commas."""

ALIASES: Dict[str, str] = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
    "hist": "history",
}

COORD_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")


class InputManager:
    """Reads commands from the user and dispatches them to the system."""

    PROMPT = "dispatch> "

    def __init__(self, system, display: Optional[DisplayManager] = None,
                 input_func: Optional[Callable[[str], str]] = None,
                 output_func: Optional[Callable[..., None]] = None) -> None:
        """Create the input manager.

        Args:
            system: The SystemManager instance.
            display: Optional DisplayManager; a default one is created.
            input_func: Function used to read lines (defaults to ``input``).
            output_func: Function used to print lines (defaults to ``print``).
        """
        self.system = system
        self.display = display or DisplayManager()
        self._input = input_func or input
        self._output = output_func or print
        self._planner = PathPlanner()
        self.history: List[str] = []
        self._handlers: Dict[str, Callable[[List[str]], Optional[bool]]] = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "tick": self._cmd_tick,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
        }
        self._enable_readline()

    # ------------------------------------------------------------------
    # Parsing and validation
    # ------------------------------------------------------------------
    @staticmethod
    def parse_command(line: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command and arguments.

        Args:
            line: Raw input line.

        Returns:
            ``(command, args)``; the command is lower-case and aliases are
            expanded. An empty line yields ``("", [])``.
        """
        tokens = line.strip().split()
        if not tokens:
            return "", []
        command = tokens[0].lower()
        return ALIASES.get(command, command), tokens[1:]

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> Tuple[int, int, int, int]:
        """Parse and validate the four order coordinates.

        Args:
            tokens: Tokens such as ``["100", "200", "300", "400"]``. Commas
                are accepted as separators.

        Returns:
            ``(restaurant_x, restaurant_y, customer_x, customer_y)``.

        Raises:
            ValueError: If the count, type or range of a value is wrong.
        """
        parts = " ".join(tokens).replace(",", " ").split()
        if len(parts) != 4:
            raise ValueError(
                "expected 4 integers (restaurant x y, customer x y), "
                f"got {len(parts)}")
        values: List[int] = []
        for label, text in zip(COORD_LABELS, parts):
            try:
                value = int(text)
            except ValueError:
                raise ValueError(
                    f"{label} must be an integer, got '{text}'") from None
            if not 0 <= value <= MAP_SIZE:
                raise ValueError(
                    f"{label} must be between 0 and {MAP_SIZE}, got {value}")
            values.append(value)
        return values[0], values[1], values[2], values[3]

    @staticmethod
    def _enable_readline() -> None:
        """Enable line editing and up-arrow history when available."""
        try:
            import readline  # noqa: F401  (side effect: line editing)
        except ImportError:
            logger.debug("readline not available; history via 'history'")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Run the interactive command loop until quit or end of input."""
        self._print(BANNER)
        while self.system.running:
            try:
                line = self._input(self.PROMPT)
            except EOFError:
                self._print("")
                break
            except KeyboardInterrupt:
                self._print("\nUse 'quit' to exit.")
                continue

            stripped = line.strip()
            if not stripped:
                continue
            if stripped == "!!":
                if not self.history:
                    self._print("Error: no previous command to repeat.")
                    continue
                stripped = self.history[-1]
                self._print(f"(repeating: {stripped})")
            self.history.append(stripped)

            try:
                keep_running = self.execute(stripped)
            except Exception as exc:  # error recovery: keep the loop alive
                logger.exception("Command failed: %s", stripped)
                self._print(f"Error: unexpected failure ({exc}). "
                            "System state is preserved.")
                keep_running = True
            if keep_running is False:
                break
        self.system.stop()

    def execute(self, line: str) -> bool:
        """Execute a single command line.

        Args:
            line: Command text.

        Returns:
            False when the program should exit, True otherwise.
        """
        command, args = self.parse_command(line)
        if not command:
            return True
        handler = self._handlers.get(command)
        if handler is None:
            self._print(f"Unknown command '{command}'. Type 'help'.")
            return True
        return handler(args) is not False

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _cmd_start(self, args: List[str]) -> None:
        """Create an order, show its route and simulate its delivery."""
        try:
            if args:
                coords = self.parse_coordinates(args)
            else:
                self._print("Enter restaurant_x restaurant_y customer_x "
                            "customer_y (0-800):")
                coords = self.parse_coordinates(self._input("  > ").split())
        except ValueError as exc:
            self._print(f"Input error: {exc}")
            return

        rx, ry, cx, cy = coords
        riders_before = len(self.system.riders)
        try:
            order = self.system.submit_order((rx, ry), (cx, cy))
        except (TypeError, ValueError) as exc:
            self._print(f"Order rejected: {exc}")
            return

        new_riders = self.system.riders[riders_before:]
        self._print(f"Order #{order.id} accepted at t={order.start_time}.")
        self._print(f"  Restaurant grid centre : {order.res_pos}")
        self._print(f"  Customer grid centre   : {order.cus_pos}")
        if new_riders:
            ids = ", ".join(f"#{r.rider_id}" for r in new_riders)
            self._print(f"  New rider added        : yes ({ids})")
        else:
            self._print("  New rider added        : no")

        if order.rider_id is None:
            self._print("  No rider available; order is pending "
                        f"(funds: {self.system.funds}).")
            return

        rider = self.system.get_rider(order.rider_id)
        route = self._planner.plan_route(rider.position, order.res_pos,
                                         order.cus_pos)
        length = path_length(route)
        ticks = math.ceil(length / rider.speed) if rider.speed else 0
        self._print(f"  Assigned to rider #{rider.rider_id} at "
                    f"({rider.x},{rider.y}), speed {rider.speed} units/tick")
        self._print(f"  Route length: {length} units (about {ticks} ticks)")
        self._print(self.display.render_map(
            riders=self.system.riders,
            orders=self.system.active_orders(),
            route=route))

        self._print("Simulating delivery ...")
        done = self.system.run_until_order_done(order)
        if done:
            self._print(
                f"Order #{order.id} delivered at t={order.completed_time}. "
                f"Time taken: {order.time_taken} tick(s), "
                f"distance: {order.distance} units, "
                f"efficiency: {order.efficiency} units/tick.")
        else:
            self._print(f"Order #{order.id} is not completed yet "
                        f"(status: {order.status}). Use 'tick' to continue.")

    def _cmd_status(self, args: List[str]) -> None:
        """Print the system status snapshot."""
        self._print(self.display.render_status(
            self.system.funds, self.system.time, self.system.riders))

    def _cmd_orders(self, args: List[str]) -> None:
        """Print the table of all orders."""
        self._print(self.display.render_orders(self.system.orders))

    def _cmd_riders(self, args: List[str]) -> None:
        """Print the event log of every rider."""
        self._print(self.display.render_rider_logs(self.system.riders))

    def _cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map."""
        self._print(self.display.render_map(
            riders=self.system.riders,
            orders=self.system.active_orders()))

    def _cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                self._print("Input error: tick count must be an integer.")
                return
            if not 1 <= count <= 1000:
                self._print("Input error: tick count must be 1-1000.")
                return
        for _ in range(count):
            self.system.tick()
        self._print(f"Advanced {count} tick(s); time is now "
                    f"{self.system.time}.")

    def _cmd_history(self, args: List[str]) -> None:
        """Print the command history."""
        if not self.history:
            self._print("History is empty.")
            return
        for index, entry in enumerate(self.history, start=1):
            self._print(f"  {index:>3}  {entry}")

    def _cmd_help(self, args: List[str]) -> None:
        """Print the help text."""
        self._print(HELP_TEXT)

    def _cmd_quit(self, args: List[str]) -> bool:
        """Stop the simulation and exit the loop."""
        self.system.stop()
        self._print("Goodbye.")
        return False

    # ------------------------------------------------------------------
    def _print(self, text: str) -> None:
        """Write a line of output through the configured output function."""
        self._output(text)
