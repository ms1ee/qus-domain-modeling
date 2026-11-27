"""Command parsing, shortcut handling, history and input validation."""

import logging

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "save": "save",
    "wait": "wait", "w": "wait",
    "history": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}

HISTORY_LIMIT = 100


class InputManager:
    """Reads, parses and validates user commands."""

    COORD_MIN = 0
    COORD_MAX = 1000

    def __init__(self, reader=None):
        """Create an input manager.

        Args:
            reader: Optional callable used to read a line (defaults to
                ``input``); injectable for testing.
        """
        self._reader = reader if reader is not None else input
        self.command_history = []

    def read_line(self, prompt="dispatch> "):
        """Read one raw line from the user, stripped of whitespace."""
        return self._reader(prompt).strip()

    def parse_command(self, line):
        """Split a command line into a canonical command name and arguments.

        Supports the shortcut ``!!`` to repeat the previous command.

        Returns:
            Tuple ``(command, args)``; ``command`` is ``""`` for blank input.

        Raises:
            ValueError: If the command is unknown or ``!!`` has no history.
        """
        line = line.strip()
        if not line:
            return "", []
        if line == "!!":
            if not self.command_history:
                raise ValueError("No previous command to repeat")
            line = self.command_history[-1]
        tokens = line.split()
        name = tokens[0].lower()
        command = COMMAND_ALIASES.get(name)
        if command is None:
            raise ValueError(
                f"Unknown command '{name}'. Type 'help' for the command list.")
        return command, tokens[1:]

    def record(self, line):
        """Add a command line to the history (skipping consecutive duplicates)."""
        if not line or line == "!!":
            return
        if self.command_history and self.command_history[-1] == line:
            return
        self.command_history.append(line)
        if len(self.command_history) > HISTORY_LIMIT:
            del self.command_history[0]

    def parse_coordinates(self, tokens):
        """Parse and validate four integer coordinates.

        Accepts space- or comma-separated values.

        Returns:
            List of four ints ``[restaurant_x, restaurant_y, customer_x,
            customer_y]``.

        Raises:
            ValueError: On wrong count, non-integer or out-of-range values.
        """
        raw = []
        for token in tokens:
            raw.extend(part for part in token.replace(",", " ").split() if part)
        if len(raw) != 4:
            raise ValueError(
                "Expected 4 integers: restaurant_x restaurant_y "
                "customer_x customer_y")
        values = []
        for token in raw:
            try:
                value = int(token)
            except ValueError as exc:
                raise ValueError(f"'{token}' is not an integer") from exc
            if not self.COORD_MIN <= value <= self.COORD_MAX:
                raise ValueError(
                    f"Coordinate {value} out of range "
                    f"({self.COORD_MIN}-{self.COORD_MAX})")
            values.append(value)
        return values

    def request_order_coordinates(self, args):
        """Return order coordinates from arguments, prompting when absent."""
        if args:
            return self.parse_coordinates(args)
        line = self.read_line(
            "Enter restaurant_x restaurant_y customer_x customer_y: ")
        return self.parse_coordinates(line.split())

    def parse_count(self, args, default=1, maximum=1000):
        """Parse an optional positive integer argument.

        Raises:
            ValueError: If the argument is not a positive integer within limits.
        """
        if not args:
            return default
        try:
            count = int(args[0])
        except ValueError as exc:
            raise ValueError(f"'{args[0]}' is not an integer") from exc
        if count < 1 or count > maximum:
            raise ValueError(f"Count must be between 1 and {maximum}")
        return count
