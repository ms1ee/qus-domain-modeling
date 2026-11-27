"""Command parsing, input validation and the interactive command loop."""

import logging
from typing import Callable, List, Optional, Sequence, Tuple

import globalvar
import system
from display import DisplayManager
from order import dispatch_pending_orders
from order_model import MAP_SIZE, Order, to_grid_center

logger = logging.getLogger(__name__)

MAX_SIMULATION_TICKS = 10000
DEFAULT_SAVE_PATH = "dispatch_state.json"

COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "save": "save",
    "history": "history", "hist": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order (restaurant x y, customer x y; 0-800).
                       Shortcut: s. Prompts for coordinates when omitted.
  status               Show funds, riders and their order lists (shortcut: st).
  orders               Show all orders with time, distance and rider (shortcut: o).
  riders               Show every rider status-change record (shortcut: r).
  map                  Show the ASCII map with riders and active orders (shortcut: m).
  save [path]          Save state to a JSON file (default dispatch_state.json).
  history              Show command history.
  !!                   Repeat the previous command.   !N  Repeat history entry N.
  help                 Show this help (shortcut: h or ?).
  quit / exit          Exit the program (shortcut: q).
"""


def parse_coordinates(tokens: Sequence[str]) -> List[int]:
    """Parse and validate four integer coordinates.

    Commas are accepted as separators in addition to whitespace.

    Args:
        tokens: Raw text tokens.

    Returns:
        A list of four integers ``[rx, ry, cx, cy]``.

    Raises:
        ValueError: If the count, type or range of any value is invalid.
    """
    text = " ".join(tokens).replace(",", " ")
    parts = text.split()
    if len(parts) != 4:
        raise ValueError(
            "Expected 4 integers: restaurant_x restaurant_y customer_x customer_y"
        )
    values: List[int] = []
    for part in parts:
        try:
            value = int(part)
        except ValueError:
            raise ValueError(f"'{part}' is not an integer") from None
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"Coordinate {value} is out of range 0-{MAP_SIZE}")
        values.append(value)
    return values


class InputManager:
    """Runs the interactive command loop and dispatches commands.

    Attributes:
        display: The DisplayManager used for all rendering.
        history: Previously entered command lines.
    """

    def __init__(
        self,
        input_func: Optional[Callable[[str], str]] = None,
        output_func: Optional[Callable[..., None]] = None,
    ) -> None:
        """Create the command manager.

        Args:
            input_func: Function used to read a line (defaults to ``input``).
            output_func: Function used to print output (defaults to ``print``).
        """
        self._input = input_func or input
        self._print = output_func or print
        self.display = DisplayManager()
        self.history: List[str] = []
        self._setup_readline()

    @staticmethod
    def _setup_readline() -> None:
        """Enable line editing and arrow-key history when readline exists."""
        try:
            import readline  # noqa: F401  pylint: disable=unused-import
        except ImportError:
            logger.debug("readline is not available on this platform")

    # ---------------------------------------------------------- main loop
    def run(self) -> None:
        """Run the command loop until the running flag is cleared."""
        self._print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while globalvar.get_value("running", True):
            try:
                line = self._input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self._print("")
                break
            line = line.strip()
            if not line:
                continue
            line = self._expand_history(line)
            if line is None:
                continue
            self.history.append(line)
            try:
                self.execute(line)
            except Exception as exc:  # error recovery: keep the loop alive
                logger.exception("Command failed: %s", line)
                self._print(f"Error: {exc}")
            for issue in system.check_consistency():
                self._print(f"[recovered] {issue}")

    def _expand_history(self, line: str) -> Optional[str]:
        """Resolve ``!!`` and ``!N`` shortcuts to previous commands.

        Args:
            line: Raw input line.

        Returns:
            The expanded command, or None if the shortcut is invalid.
        """
        if line == "!!":
            if not self.history:
                self._print("No previous command.")
                return None
            return self.history[-1]
        if line.startswith("!") and line[1:].isdigit():
            index = int(line[1:])
            if not 1 <= index <= len(self.history):
                self._print(f"No history entry {index}.")
                return None
            return self.history[index - 1]
        return line

    def execute(self, line: str) -> None:
        """Parse and run a single command line.

        Args:
            line: The command text.
        """
        parts = line.split()
        name = COMMAND_ALIASES.get(parts[0].lower())
        args = parts[1:]
        if name is None:
            self._print(f"Unknown command '{parts[0]}'. Type 'help' for a list.")
            return
        handler = getattr(self, f"cmd_{name}")
        handler(args)

    # ------------------------------------------------------------ commands
    def cmd_help(self, _args: List[str]) -> None:
        """Print the help text."""
        self._print(HELP_TEXT)

    def cmd_history(self, _args: List[str]) -> None:
        """Print the numbered command history."""
        if not self.history:
            self._print("History is empty.")
            return
        for index, entry in enumerate(self.history, start=1):
            self._print(f"{index:>4}  {entry}")

    def cmd_quit(self, _args: List[str]) -> None:
        """Stop the main loop."""
        globalvar.set_value("running", False)
        self._print("Goodbye.")

    def cmd_status(self, _args: List[str]) -> None:
        """Print the system status snapshot."""
        pending = globalvar.get_value("pending_orders") or []
        self._print(self.display.render_status(
            system.get_funds(), system.get_riders(), len(pending)))

    def cmd_orders(self, _args: List[str]) -> None:
        """Print every order with time, distance and rider information."""
        self._print(self.display.render_orders(globalvar.get_value("all_orders") or []))

    def cmd_riders(self, _args: List[str]) -> None:
        """Print every rider's recorded status changes."""
        self._print(self.display.render_rider_logs(system.get_riders()))

    def cmd_map(self, _args: List[str]) -> None:
        """Print the ASCII map with riders and active orders."""
        orders = [o for o in (globalvar.get_value("all_orders") or [])
                  if o.status != "completed"]
        self._print(self.display.render_map(system.get_riders(), orders))

    def cmd_save(self, args: List[str]) -> None:
        """Save state to a JSON file.

        Args:
            args: Optional output path.
        """
        path = args[0] if args else DEFAULT_SAVE_PATH
        system.save_config(path)
        self._print(f"State saved to {path}")

    def cmd_start(self, args: List[str]) -> None:
        """Place an order, dispatch it and simulate until it is delivered.

        Args:
            args: Optional four coordinate tokens. When omitted the coordinates
                are requested interactively.
        """
        tokens = list(args)
        if not tokens:
            tokens = [self._input("Enter restaurant x y and customer x y (0-800): ")]
        try:
            coords = parse_coordinates(tokens)
        except ValueError as exc:
            self._print(f"Invalid input: {exc}")
            return
        self.place_order(coords)

    # ------------------------------------------------------- order workflow
    def place_order(self, coords: Sequence[int]) -> None:
        """Create an order, dispatch it and report the delivery route.

        Args:
            coords: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.
        """
        order = Order(coords[0:2], coords[2:4])
        pending = globalvar.get_value("pending_orders")
        pending.append(order)

        assignments, new_riders = dispatch_pending_orders()
        if order.status == "pending" or order.rider_id is None:
            self._print(
                f"Order #{order.id} queued: no rider available and funds are "
                f"insufficient to recruit one (funds {system.get_funds()})."
            )
            return

        rider = system.find_rider(order.rider_id)
        route: List[Tuple[int, int]] = [(rider.x, rider.y)]
        ticks = 0
        while order.status != "completed" and ticks < MAX_SIMULATION_TICKS:
            system.advance_tick()
            _, more_new = dispatch_pending_orders()
            new_riders.extend(more_new)
            ticks += 1
            route.append((rider.x, rider.y))

        if order.status != "completed":
            self._print(f"Order #{order.id} did not finish within {MAX_SIMULATION_TICKS} ticks.")
            return

        self._print_order_report(order, rider, route, new_riders, coords)

    def _print_order_report(
        self,
        order: Order,
        rider,
        route: List[Tuple[int, int]],
        new_riders: list,
        coords: Sequence[int],
    ) -> None:
        """Print the summary and route map for a delivered order.

        Args:
            order: The completed order.
            rider: The rider that served the order.
            route: Positions visited by the rider, one per tick.
            new_riders: Riders recruited while processing this order.
            coords: The coordinates entered by the user.
        """
        rgrid = to_grid_center(coords[0], coords[1])
        cgrid = to_grid_center(coords[2], coords[3])
        recruited = "yes" if new_riders else "no"
        lines = [
            f"Order #{order.id} delivered.",
            f"  Restaurant: input ({coords[0]}, {coords[1]}) -> grid {rgrid}",
            f"  Customer:   input ({coords[2]}, {coords[3]}) -> grid {cgrid}",
            f"  New rider added: {recruited}"
            + (f" (rider #{', #'.join(str(r.rider_id) for r in new_riders)})"
               if new_riders else ""),
            f"  Assigned rider: #{rider.rider_id} | speed {rider.speed} units/tick",
            f"  Time taken: {order.time_taken} ticks | distance {order.distance} | "
            f"efficiency {order.efficiency} units/tick",
            "  Route map:",
            self.display.render_map(riders=[rider], route=route),
        ]
        self._print("\n".join(lines))
