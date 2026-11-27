"""Command parsing, shortcut resolution, history and input validation."""

from typing import List, Sequence, Tuple

COORDINATE_NAMES = ("restaurant_x", "restaurant_y",
                    "customer_x", "customer_y")
MAX_HISTORY = 100

ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "save": "save",
    "history": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order (restaurant then customer, 0-800).
                       Runs the simulation until the order is delivered.
  status (st)          Funds, time, and every rider's status and orders.
  orders (o)           Details of all orders.
  riders (r)           Event log of every rider status change.
  map (m)              ASCII map with riders, restaurants and customers.
  tick [n]             Advance the simulation by n ticks (default 1).
  save [path]          Save the state to a JSON file.
  history              Show recent commands.
  help (h, ?)          Show this help.
  quit (q, exit)       Leave the program.
Shortcuts: '!!' repeats the last command, '!n' repeats history entry n.
"""


class CommandError(Exception):
    """Raised for invalid user input or unknown commands."""


class InputManager:
    """Parses command lines and validates user input.

    Attributes:
        command_history: Previously entered command lines (oldest first).
    """

    def __init__(self, max_history: int = MAX_HISTORY) -> None:
        """Create an input manager with an empty history.

        Args:
            max_history: Maximum number of history entries kept.
        """
        self.command_history: List[str] = []
        self._max_history = max_history

    def _record(self, raw: str) -> None:
        """Append a command to the history, trimming old entries."""
        self.command_history.append(raw)
        overflow = len(self.command_history) - self._max_history
        if overflow > 0:
            del self.command_history[:overflow]

    def resolve_line(self, line: str) -> Tuple[str, List[str]]:
        """Resolve a raw input line into a canonical command and arguments.

        Handles shortcut keys, '!!' and '!n' history recall.

        Args:
            line: Raw user input.

        Returns:
            Tuple of (canonical command name, argument token list).

        Raises:
            CommandError: For empty input, unknown commands or invalid
                history references.
        """
        raw = line.strip()
        if raw == "!!":
            if not self.command_history:
                raise CommandError("No previous command in history.")
            raw = self.command_history[-1]
        elif raw.startswith("!") and raw[1:].isdigit():
            index = int(raw[1:])
            if not 1 <= index <= len(self.command_history):
                raise CommandError(f"No history entry #{index}.")
            raw = self.command_history[index - 1]

        tokens = raw.split()
        if not tokens:
            raise CommandError("Empty command. Type 'help' for commands.")
        name = tokens[0].lower()
        command = ALIASES.get(name)
        if command is None:
            raise CommandError(f"Unknown command '{name}'. Type 'help'.")
        self._record(raw)
        return command, tokens[1:]

    def parse_coordinates(self, tokens: Sequence[str]) -> List[int]:
        """Validate four integer coordinates in the range 0-800.

        Commas are accepted as separators, e.g. ``100,200 400,500``.

        Args:
            tokens: Raw coordinate tokens.

        Returns:
            [restaurant_x, restaurant_y, customer_x, customer_y].

        Raises:
            CommandError: If the count, type or range is invalid.
        """
        parts: List[str] = []
        for token in tokens:
            parts.extend(token.replace(",", " ").split())
        if len(parts) != 4:
            raise CommandError(
                "Expected 4 integer coordinates: restaurant_x restaurant_y "
                f"customer_x customer_y (got {len(parts)})")
        values: List[int] = []
        for label, text in zip(COORDINATE_NAMES, parts):
            try:
                value = int(text)
            except ValueError:
                raise CommandError(
                    f"{label} must be an integer, got '{text}'") from None
            if not 0 <= value <= 800:
                raise CommandError(
                    f"{label} must be within 0-800, got {value}")
            values.append(value)
        return values

    def parse_count(self, tokens: Sequence[str], default: int = 1,
                    maximum: int = 10000) -> int:
        """Parse an optional positive tick count argument.

        Raises:
            CommandError: If the argument is not a positive integer within
                the allowed maximum.
        """
        if not tokens:
            return default
        try:
            value = int(tokens[0])
        except ValueError:
            raise CommandError(f"Tick count must be an integer, got "
                               f"'{tokens[0]}'") from None
        if not 1 <= value <= maximum:
            raise CommandError(f"Tick count must be between 1 and {maximum}")
        return value

    @staticmethod
    def help_text() -> str:
        """Return the command help text."""
        return HELP_TEXT
