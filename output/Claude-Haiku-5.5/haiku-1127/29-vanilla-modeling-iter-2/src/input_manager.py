"""Command-line parsing, dispatch and input validation."""

import logging
import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from config import save_state
from order import find_best_rider_for_order
from order_model import validate_order_coords
from path_planner import cell_index

try:  # Command history and line editing where available.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

logger = logging.getLogger(__name__)

PROMPT = "dispatch> "
MAX_TICKS_PER_COMMAND = 100000
DEFAULT_SAVE_PATH = "dispatch_state.json"

ALIASES: Dict[str, str] = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "t": "tick",
    "m": "map",
    "w": "save",
    "h": "help",
    "?": "help",
    "hist": "history",
    "q": "quit",
    "x": "exit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant then customer, 0-800).
                       Prompts for the four integers when none are given.
  status (st)          System funds, riders, their state and orders.
  orders (o)           Details of all orders.
  riders (r)           Status change log for every rider.
  tick [n] (t)         Advance the simulation by n ticks (default 1).
  map (m)              Show the ASCII map with riders and orders.
  save [path] (w)      Save parameters, rider info and order history to JSON.
  history (hist)       Show previously entered commands.
  !!                   Repeat the last command.
  help (h, ?)          Show this help.
  quit (q) / exit (x)  Leave the program."""


class InputManager:
    """Reads commands, validates input and dispatches to handlers.

    Attributes:
        system: The ``SystemManager``.
        order_manager: The ``OrderManager``.
        display: The ``DisplayManager``.
        command_history: Every command entered, in order.
        input_func: Function used to read a line (injectable for testing).
        output_func: Function used to print messages.
    """

    def __init__(self, system: Any, order_manager: Any, display: Any,
                 input_func: Callable[[str], str] = input,
                 output_func: Callable[[str], Any] = print) -> None:
        """Create the input manager.

        Args:
            system: System manager.
            order_manager: Order manager.
            display: Display manager.
            input_func: Line reader.
            output_func: Output writer.
        """
        self.system = system
        self.order_manager = order_manager
        self.display = display
        self.input_func = input_func
        self.output_func = output_func
        self.command_history: List[str] = []
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "tick": self.cmd_tick,
            "map": self.cmd_map,
            "save": self.cmd_save,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    def output(self, message: str = "") -> None:
        """Write a message to the user."""
        self.output_func(message)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Run the interactive command loop until quit or end of input."""
        self.output("Food delivery dispatch simulator. Type 'help' for commands.")
        while self.system.is_running:
            try:
                raw = self.input_func(PROMPT)
            except (EOFError, KeyboardInterrupt):
                self.output("")
                break
            try:
                self.execute(raw)
            except Exception as exc:  # noqa: BLE001 - recover and continue
                logger.exception("Command failed: %r", raw)
                self.output(f"Error: {exc}. Checking system state...")
                repaired = self.system.repair_state()
                if repaired:
                    self.output(f"Recovered {repaired} rider state(s).")
        self.output("Goodbye.")

    def execute(self, raw: str) -> None:
        """Parse one command line and run its handler.

        Args:
            raw: The raw text entered by the user.
        """
        line = raw.strip()
        if not line:
            return
        if line == "!!":
            if not self.command_history:
                self.output("No previous command to repeat.")
                return
            line = self.command_history[-1]
            self.output(f"Repeating: {line}")
        self.command_history.append(line)

        parts = line.split()
        name = parts[0].lower()
        command = ALIASES.get(name, name)
        handler = self._handlers.get(command)
        if handler is None:
            self.output(f"Unknown command '{parts[0]}'. Type 'help' for a list of commands.")
            return
        handler(parts[1:])

    # ------------------------------------------------------------------
    # Parsing and validation
    # ------------------------------------------------------------------
    @staticmethod
    def parse_coordinates(text: str) -> List[int]:
        """Parse and validate four order coordinates.

        Args:
            text: Text containing four integers separated by spaces or commas.

        Returns:
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the count, type or range is wrong.
        """
        parts = text.replace(",", " ").split()
        if len(parts) != 4:
            raise ValueError(
                f"expected 4 integers (restaurant_x restaurant_y customer_x "
                f"customer_y) but got {len(parts)}")
        values: List[int] = []
        for part in parts:
            try:
                values.append(int(part))
            except ValueError:
                raise ValueError(f"'{part}' is not an integer") from None
        return validate_order_coords(values)

    def _prompt_for_coordinates(self) -> Optional[List[int]]:
        """Ask the user for coordinates until valid input or cancellation.

        Returns:
            The validated coordinates, or None if the user cancelled.
        """
        while True:
            try:
                text = self.input_func(
                    "Enter restaurant_x restaurant_y customer_x customer_y "
                    "(blank to cancel): ").strip()
            except (EOFError, KeyboardInterrupt):
                return None
            if not text:
                return None
            try:
                return self.parse_coordinates(text)
            except ValueError as exc:
                self.output(f"Invalid input: {exc}. Please try again.")

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def cmd_start(self, args: List[str]) -> None:
        """Create an order, assign a rider and show the route map."""
        if args:
            try:
                coords = self.parse_coordinates(" ".join(args))
            except ValueError as exc:
                self.output(f"Invalid input: {exc}")
                return
        else:
            coords = self._prompt_for_coordinates()
            if coords is None:
                self.output("Order entry cancelled.")
                return
        self._dispatch_order(coords)

    def _dispatch_order(self, coords: Sequence[int]) -> None:
        """Create, recruit for, assign and report an order."""
        riders_before = len(self.system.riders)
        order = self.order_manager.create_order(coords)
        self.system.maybe_recruit(self.order_manager.pending_count())
        new_riders = self.system.riders[riders_before:]

        rider = find_best_rider_for_order(order)
        if rider is None:
            self.output(f"Order #{order.id} stays pending: no rider available "
                        f"(funds {self.system.funds}).")
            return
        self.order_manager.assign(order, rider)

        start = rider.position
        waypoints = rider.planner.plan_route(start, order.res_pos, order.cus_pos)
        length = rider.planner.path_length(start, waypoints)
        eta = math.ceil(length / rider.speed) if rider.speed > 0 else 0

        rx, ry = order.res_pos
        cx, cy = order.cus_pos
        self.output(f"Order #{order.id} accepted.")
        self.output(f"  Restaurant: input {tuple(coords[:2])} -> grid cell "
                    f"(col {cell_index(rx)}, row {cell_index(ry)}), centre ({rx}, {ry})")
        self.output(f"  Customer:   input {tuple(coords[2:])} -> grid cell "
                    f"(col {cell_index(cx)}, row {cell_index(cy)}), centre ({cx}, {cy})")
        if new_riders:
            added = ", ".join(f"#{r.rider_id}" for r in new_riders)
            self.output(f"  New rider added: yes ({added}); funds now {self.system.funds}")
        else:
            self.output("  New rider added: no")
        self.output(f"  Assigned rider: #{rider.rider_id} at ({rider.x}, {rider.y}), "
                    f"speed {rider.speed} units/tick, status {rider.state_name}")
        self.output(f"  Route length: {length} units, estimated ticks: {eta} "
                    f"(from the rider's current position)")
        self.output("  Route map:")
        self.output(self.display.render(route=[start] + waypoints, route_start=start))

    def cmd_status(self, args: List[str]) -> None:
        """Show the system snapshot and consistency results."""
        self.output(self.display.status_text())
        issues = self.system.check_consistency()
        if issues:
            self.output("Consistency warnings:")
            for issue in issues:
                self.output(f"  - {issue}")
        else:
            self.output("Consistency check: OK")

    def cmd_orders(self, args: List[str]) -> None:
        """Show details of all orders."""
        self.output(self.display.orders_text())

    def cmd_riders(self, args: List[str]) -> None:
        """Show every recorded rider status change."""
        self.output(self.display.riders_text())

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation clock by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                self.output("Tick count must be an integer.")
                return
        if not 1 <= count <= MAX_TICKS_PER_COMMAND:
            self.output(f"Tick count must be between 1 and {MAX_TICKS_PER_COMMAND}.")
            return
        completed_before = len(self.order_manager.completed_orders())
        for _ in range(count):
            self.system.tick()
        delivered = len(self.order_manager.completed_orders()) - completed_before
        self.output(f"Advanced {count} tick(s). Current tick: {self.system.current_tick}. "
                    f"Deliveries completed: {delivered}. Funds: {self.system.funds}.")

    def cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map."""
        self.output(self.display.render())

    def cmd_save(self, args: List[str]) -> None:
        """Save the simulation state to a JSON file."""
        path = args[0] if args else DEFAULT_SAVE_PATH
        try:
            save_state(path, self.system, self.order_manager)
        except OSError as exc:
            self.output(f"Could not save state: {exc}")
            return
        self.output(f"State saved to {path}.")

    def cmd_history(self, args: List[str]) -> None:
        """List previously entered commands."""
        if not self.command_history:
            self.output("No commands entered yet.")
            return
        for index, command in enumerate(self.command_history, start=1):
            self.output(f"  {index:>3}  {command}")

    def cmd_help(self, args: List[str]) -> None:
        """Show the command help."""
        self.output(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the simulator."""
        self.system.shutdown()
