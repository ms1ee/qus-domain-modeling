"""Command parsing, validation and the interactive main loop."""

import logging
import re
from typing import Any, Callable, Dict, List, Optional

try:  # Enables line editing and arrow-key history where available.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    pass

from config import DEFAULT_SAVE_PATH, MAP_SIZE, MAX_INPUT_ATTEMPTS
from display import DisplayManager
from order_model import Order
from rider import Rider
from system import SystemManager

logger = logging.getLogger(__name__)

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant then customer, 0-800)
  status  (s)          System funds, riders and map
  orders  (o)          Details of all orders
  riders  (r)          Status-change log of every rider
  map     (m)          ASCII map of riders and active orders
  tick [n] (t)         Advance the simulation n ticks (default 1)
  save [path]          Save system state to JSON
  history (h)          Show command history
  help    (?)          Show this help
  quit    (q)/exit     Exit the program
Every command except help/history/tick/quit advances the simulation by one tick."""

COMMAND_ALIASES = {
    "s": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "history",
    "?": "help",
    "q": "quit",
    "x": "exit",
}

NO_AUTO_TICK = {"help", "history", "tick", "quit", "exit", "unknown"}


def parse_coordinates(text: str) -> List[int]:
    """Parse four integer coordinates from user text.

    Accepts whitespace, commas or brackets as separators.

    Args:
        text: Raw user input, e.g. ``"100 200 300 400"``.

    Returns:
        List ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

    Raises:
        ValueError: If the count, type or range of the values is invalid.
    """
    tokens = [tok for tok in re.split(r"[\s,\[\]]+", text.strip()) if tok]
    if len(tokens) != 4:
        raise ValueError(
            f"expected 4 integers (restaurant_x restaurant_y customer_x customer_y), "
            f"got {len(tokens)}"
        )
    values: List[int] = []
    for token in tokens:
        try:
            values.append(int(token))
        except ValueError:
            raise ValueError(f"'{token}' is not an integer") from None
    for value in values:
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"coordinate {value} is out of range 0-{MAP_SIZE}")
    return values


class InputManager:
    """Reads commands, dispatches them and drives the simulation loop."""

    def __init__(
        self,
        system: SystemManager,
        display: DisplayManager,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], Any] = print,
    ) -> None:
        """Create the input manager.

        Args:
            system: The system manager controlling the simulation.
            display: Display manager used for all output reports.
            input_func: Function used to read a line (injectable for tests).
            output_func: Function used to write a line of output.
        """
        self.system = system
        self.display = display
        self._input = input_func
        self._print = output_func
        self.history: List[str] = []
        self._auto_tick = True
        self._handlers: Dict[str, Callable[[List[str]], bool]] = {
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

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Run the interactive loop until quit, EOF or interrupt.

        Each iteration processes one command and then advances the
        simulation by one tick (unless the command does not advance time).
        """
        self._print(HELP_TEXT)
        while self.system.running:
            try:
                line = self._input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self._print("")
                break
            line = line.strip()
            if not line:
                continue
            self.history.append(line)
            self._auto_tick = True
            try:
                keep_running = self.execute(line)
            except (EOFError, KeyboardInterrupt):
                self._print("")
                break
            except Exception as exc:  # graceful error recovery
                logger.exception("Command failed: %s", line)
                self._print(f"Error: {exc}. The command was ignored.")
                keep_running = True
            if not keep_running:
                break
            if self._auto_tick:
                self._run_tick()
        self._print("Simulation ended. Goodbye!")

    def execute(self, line: str) -> bool:
        """Parse and run a single command line.

        Args:
            line: Command text entered by the user.

        Returns:
            False if the program should exit, True otherwise.
        """
        parts = line.split()
        name = parts[0].lower()
        command = COMMAND_ALIASES.get(name, name)
        handler = self._handlers.get(command)
        if handler is None:
            self._auto_tick = False
            self._print(f"Unknown command '{parts[0]}'. Type 'help' for a list of commands.")
            return True
        return handler(parts[1:])

    # ------------------------------------------------------------------
    # Tick handling
    # ------------------------------------------------------------------
    def _run_tick(self) -> None:
        """Advance the simulation by one tick and print notable events."""
        result = self.system.tick()
        time = result["time"]
        for rider_id, entry in result["events"]:
            order_id = entry["order_id"]
            if entry["event"] == "arrived_at_merchant":
                message = f"Rider #{rider_id} reached the restaurant for order #{order_id} and is delivering it."
            elif entry["event"] == "delivered_to_customer":
                message = f"Rider #{rider_id} delivered order #{order_id}."
            else:
                message = f"Rider #{rider_id}: {entry['event']} (order #{order_id})."
            self._print(f"[t={time}] {message}")
        for order in result["assigned"]:
            self._print(f"[t={time}] Order #{order.id} assigned to rider #{order.rider_id}.")
        for error in result["errors"]:
            self._print(f"[t={time}] Recovered from error: {error}")
        for fix in result["fixes"]:
            self._print(f"[t={time}] State repaired: {fix}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _try_parse(self, text: str) -> Optional[List[int]]:
        """Parse coordinates, printing an error message on failure."""
        try:
            return parse_coordinates(text)
        except ValueError as exc:
            self._print(f"Invalid input: {exc}.")
            return None

    def _find_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with the given id, if it exists."""
        for rider in self.system.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    # ------------------------------------------------------------------
    # Command handlers (each returns True to keep running)
    # ------------------------------------------------------------------
    def _cmd_start(self, args: List[str]) -> bool:
        """Create an order from four coordinates and dispatch it."""
        values: Optional[List[int]] = None
        if args:
            values = self._try_parse(" ".join(args))
            if values is None:
                return True
        else:
            self._print("Enter: restaurant_x restaurant_y customer_x customer_y (0-800)")
            for _ in range(MAX_INPUT_ATTEMPTS):
                text = self._input("start> ")
                values = self._try_parse(text)
                if values is not None:
                    break
            else:
                self._print("Too many invalid attempts; the order was cancelled.")
                return True

        try:
            order = self.system.order_manager.create_order(
                (values[0], values[1]), (values[2], values[3])
            )
        except ValueError as exc:
            self._print(f"Invalid order: {exc}.")
            return True

        new_riders, _assigned = self.system.dispatch()
        if order.rider_id is None:
            self._print(self.display.queued_report(order, self.system.funds))
            return True
        rider = self._find_rider(order.rider_id)
        if rider is None:  # state consistency guard
            self._print(f"Error: rider #{order.rider_id} not found for order #{order.id}.")
            return True
        self._print(self.display.start_report(order, rider, bool(new_riders)))
        return True

    def _cmd_status(self, _args: List[str]) -> bool:
        """Show a snapshot of funds, riders and the map."""
        self._print(self.display.status_report(self.system))
        return True

    def _cmd_orders(self, _args: List[str]) -> bool:
        """Show details of all orders."""
        self._print(self.display.orders_report(self.system.order_manager.history))
        return True

    def _cmd_riders(self, _args: List[str]) -> bool:
        """Show the status-change log of all riders."""
        self._print(self.display.rider_log_report(self.system.riders))
        return True

    def _cmd_map(self, _args: List[str]) -> bool:
        """Show the ASCII map of riders and active orders."""
        self._print(self.display.render_map(
            self.system.riders, self.system.order_manager.active_orders()))
        return True

    def _cmd_tick(self, args: List[str]) -> bool:
        """Advance the simulation a number of ticks."""
        self._auto_tick = False
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                self._print(f"Invalid tick count '{args[0]}': must be an integer.")
                return True
            if not 1 <= count <= 1000:
                self._print("Tick count must be between 1 and 1000.")
                return True
        for _ in range(count):
            self._run_tick()
        return True

    def _cmd_save(self, args: List[str]) -> bool:
        """Save the system state to a JSON file."""
        self._auto_tick = False
        path = args[0] if args else DEFAULT_SAVE_PATH
        try:
            saved = self.system.save_state(path)
        except OSError as exc:
            self._print(f"Could not save state: {exc}.")
            return True
        self._print(f"State saved to {saved}.")
        return True

    def _cmd_history(self, _args: List[str]) -> bool:
        """Show the command history."""
        self._auto_tick = False
        if not self.history:
            self._print("No commands yet.")
        for index, line in enumerate(self.history, start=1):
            self._print(f"{index:>4}  {line}")
        return True

    def _cmd_help(self, _args: List[str]) -> bool:
        """Show the command help."""
        self._auto_tick = False
        self._print(HELP_TEXT)
        return True

    def _cmd_quit(self, _args: List[str]) -> bool:
        """Stop the simulation and exit."""
        self._auto_tick = False
        self.system.stop()
        return False
