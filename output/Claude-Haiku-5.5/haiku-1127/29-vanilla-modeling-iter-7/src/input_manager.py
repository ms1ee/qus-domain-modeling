"""Command parsing, input validation and command dispatch."""

import logging
import math

from order_model import OrderValidationError
from path_planner import estimate_route
from rider import STATE_IDLE

logger = logging.getLogger(__name__)

MAP_MIN = 0
MAP_MAX = 800
COORDINATE_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")

HELP_TEXT = """Commands:
  start <rx> <ry> <cx> <cy>  Create an order (restaurant and customer, 0-800).
                             Prompts for missing values.
  status   (s)               Show system funds and every rider's status.
  orders   (o)               Show details for all orders.
  riders   (r)               Show every rider status change event.
  map      (m)               Show the ASCII map with riders and orders.
  tick [n] (t)               Advance the simulation by n ticks (default 1).
  save [file]                Save state to a JSON file (default dispatch_state.json).
  history                    Show command history.
  !!                         Repeat the previous command.
  help     (h)               Show this help.
  quit     (q) / exit        Exit the simulator.
Each loop iteration also advances the simulation by one tick."""


class InputError(Exception):
    """Raised for invalid user input; the message is shown to the user."""


def parse_coordinate(token, label):
    """Parse and validate one coordinate token.

    Args:
        token: Raw text token.
        label: Human-readable name used in error messages.

    Returns:
        Integer coordinate in range 0-800.

    Raises:
        InputError: If the token is not an integer or out of range.
    """
    try:
        value = int(token)
    except (TypeError, ValueError):
        raise InputError(f"{label} must be an integer, got '{token}'.")
    if not MAP_MIN <= value <= MAP_MAX:
        raise InputError(f"{label} must be between {MAP_MIN} and {MAP_MAX}, got {value}.")
    return value


class InputManager:
    """Parses and executes user commands.

    Attributes:
        system: The ``SystemManager`` being controlled.
        display: The ``DisplayManager`` used for output.
        command_history: List of executed command lines.
    """

    SHORTCUTS = {
        "s": "status",
        "o": "orders",
        "r": "riders",
        "m": "map",
        "t": "tick",
        "h": "help",
        "q": "quit",
    }

    def __init__(self, system, display):
        """Create the input manager.

        Args:
            system: The ``SystemManager`` instance.
            display: The ``DisplayManager`` instance.
        """
        self.system = system
        self.display = display
        self.command_history = []
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

    def execute(self, line, reader=input):
        """Parse and run one command line.

        Args:
            line: Raw input line.
            reader: Callable used to prompt for missing values (default ``input``).

        Returns:
            Text to display to the user (may be empty).
        """
        raw = (line or "").strip()
        if not raw:
            return ""
        if raw == "!!":
            if not self.command_history:
                return "No previous command to repeat."
            raw = self.command_history[-1]
        self.command_history.append(raw)

        tokens = raw.split()
        name = tokens[0].lower()
        name = self.SHORTCUTS.get(name, name)
        handler = self._handlers.get(name)
        if handler is None:
            return f"Unknown command '{tokens[0]}'. Type 'help' for available commands."
        try:
            return handler(tokens[1:], reader)
        except InputError as exc:
            return f"Error: {exc}"
        except OSError as exc:
            return f"Error: file operation failed: {exc}"

    def _cmd_start(self, args, reader):
        """Create an order from four coordinates and report the assignment."""
        if len(args) > 4:
            raise InputError("start expects exactly 4 coordinates: restaurant x y, customer x y.")
        values = []
        for index, label in enumerate(COORDINATE_LABELS):
            if index < len(args):
                token = args[index]
            else:
                token = reader(f"Enter {label} (0-{MAP_MAX}): ")
            values.append(parse_coordinate(str(token).strip(), label.capitalize()))
        restaurant = (values[0], values[1])
        customer = (values[2], values[3])
        try:
            result = self.system.submit_order(restaurant, customer)
        except OrderValidationError as exc:
            raise InputError(str(exc))
        return self._format_start(result)

    def _format_start(self, result):
        """Build the output text for a successfully created order."""
        order = result["order"]
        rider = result["rider"]
        lines = [
            f"Order #{order.id} accepted.",
            f"Restaurant grid point: {order.restaurant}",
            f"Customer grid point: {order.customer}",
            f"New rider recruited: {'yes' if result['new_rider'] else 'no'}",
        ]
        if rider is None:
            lines.append("No rider available; the order stays pending and is retried every tick.")
            return "\n".join(lines)

        distance = math.hypot(rider.x - order.restaurant[0], rider.y - order.restaurant[1])
        points = estimate_route(rider.x, rider.y, order.restaurant, order.customer)
        ticks = math.ceil(len(points) / rider.speed) if points else 0
        lines.append(
            f"Assigned rider: #{rider.rider_id} (distance to restaurant {distance:.1f})"
        )
        lines.append(
            f"Route speed: {rider.speed} units/tick; route length {len(points)} units; "
            f"estimated time {ticks} tick(s) (this order only)."
        )
        lines.append(self.display.render_map(route_points=points))
        return "\n".join(lines)

    def _cmd_status(self, args, reader):
        """Show the system status snapshot."""
        return self.display.render_status()

    def _cmd_orders(self, args, reader):
        """Show all order details."""
        return self.display.render_orders()

    def _cmd_riders(self, args, reader):
        """Show all rider event logs."""
        return self.display.render_rider_log()

    def _cmd_map(self, args, reader):
        """Show the ASCII map."""
        return self.display.render_map()

    def _cmd_tick(self, args, reader):
        """Advance the simulation by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise InputError(f"tick count must be an integer, got '{args[0]}'.")
            if not 1 <= count <= 1000:
                raise InputError("tick count must be between 1 and 1000.")
        for _ in range(count):
            self.system.tick()
        return f"Advanced {count} tick(s). Current tick: {self.system.current_tick}."

    def _cmd_save(self, args, reader):
        """Save the system snapshot to a JSON file."""
        path = args[0] if args else "dispatch_state.json"
        self.system.save_snapshot(path)
        return f"System state saved to {path}."

    def _cmd_history(self, args, reader):
        """Show executed command history."""
        if not self.command_history:
            return "No commands in history."
        return "\n".join(f"{i}: {cmd}" for i, cmd in enumerate(self.command_history, 1))

    def _cmd_help(self, args, reader):
        """Show the command help text."""
        return HELP_TEXT

    def _cmd_quit(self, args, reader):
        """Stop the simulator main loop."""
        self.system.stop()
        return "Shutting down the dispatch simulator..."
