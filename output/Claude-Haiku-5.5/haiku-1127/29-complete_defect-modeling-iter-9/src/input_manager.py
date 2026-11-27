"""Command parsing, shortcut resolution, history and input validation."""

import re
from dataclasses import dataclass, field

from config import MAP_SIZE, MAX_HISTORY

COMMANDS = {"start", "status", "orders", "riders", "map", "wait",
            "history", "help", "quit", "exit"}

ALIASES = {
    "a": "start",
    "s": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "w": "wait",
    "h": "help",
    "?": "help",
    "q": "quit",
}

COORDINATE_LABELS = ["restaurant x", "restaurant y", "customer x", "customer y"]


@dataclass
class Command:
    """A parsed user command.

    Attributes:
        name: Canonical command name.
        arguments: Remaining tokens after the command name.
    """

    name: str
    arguments: list = field(default_factory=list)


class InputManager:
    """Parses user input, resolves shortcuts and validates coordinates.

    Attributes:
        command_history: Previously entered command lines (most recent last).
    """

    def __init__(self, max_history: int = MAX_HISTORY):
        """Create an input manager with an empty history.

        Args:
            max_history: Maximum number of remembered command lines.
        """
        self.command_history = []
        self._max_history = max_history

    def resolve_line(self, line: str) -> str:
        """Expand history shortcuts ``!!`` and ``!n`` into a command line.

        Args:
            line: Raw input line.

        Returns:
            str: The resolved command line.

        Raises:
            ValueError: If the referenced history entry does not exist.
        """
        stripped = line.strip()
        if stripped == "!!":
            if not self.command_history:
                raise ValueError("no previous command in history")
            return self.command_history[-1]
        match = re.fullmatch(r"!(\d+)", stripped)
        if match:
            index = int(match.group(1))
            if not 1 <= index <= len(self.command_history):
                raise ValueError(f"no history entry {index}")
            return self.command_history[index - 1]
        return stripped

    def record(self, line: str) -> None:
        """Store a non-empty command line in the history.

        Args:
            line: Resolved command line.
        """
        if line.strip():
            self.command_history.append(line.strip())
            if len(self.command_history) > self._max_history:
                del self.command_history[0]

    def parse(self, line: str) -> Command:
        """Parse a command line into a Command.

        Args:
            line: Resolved command line (may be empty).

        Returns:
            Command: The parsed command. An empty line yields a no-op
            command named "" which the application treats as idle.

        Raises:
            ValueError: If the command name is unknown.
        """
        tokens = line.strip().split()
        if not tokens:
            return Command("", [])
        name = tokens[0].lower()
        name = ALIASES.get(name, name)
        if name not in COMMANDS:
            raise ValueError(f"unknown command '{tokens[0]}'. Type 'help' for a list.")
        return Command(name, tokens[1:])

    @staticmethod
    def parse_coordinate(token, label: str = "coordinate") -> int:
        """Convert a token to an integer coordinate in the range 0-800.

        Args:
            token: Raw token (string or int).
            label: Human readable name for error messages.

        Returns:
            int: Validated coordinate.

        Raises:
            ValueError: If the token is not an integer or is out of range.
        """
        try:
            value = int(str(token).strip())
        except ValueError:
            raise ValueError(f"{label} must be an integer, got '{token}'") from None
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"{label} {value} is out of range 0-{MAP_SIZE}")
        return value

    def validate_coordinates(self, tokens) -> list:
        """Validate exactly four coordinate tokens.

        Args:
            tokens: Sequence of four raw tokens.

        Returns:
            list[int]: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the count is wrong or any value is invalid.
        """
        if len(tokens) != 4:
            raise ValueError("expected 4 coordinates: restaurant_x restaurant_y "
                             "customer_x customer_y")
        return [self.parse_coordinate(tok, label)
                for tok, label in zip(tokens, COORDINATE_LABELS)]

    def prompt_coordinates(self, input_func, output) -> list:
        """Interactively prompt for four coordinates with re-prompting on error.

        Args:
            input_func: Callable used to read a line (e.g. ``input``).
            output: Callable used to print messages (e.g. ``print``).

        Returns:
            list[int]: Four validated coordinates.
        """
        output(f"Enter coordinates (0-{MAP_SIZE}):")
        values = []
        for label in COORDINATE_LABELS:
            while True:
                raw = input_func(f"  {label}: ")
                try:
                    values.append(self.parse_coordinate(raw, label))
                    break
                except ValueError as exc:
                    output(f"Error: {exc}. Please try again.")
        return values

    @staticmethod
    def help_text() -> str:
        """Return the help text listing all commands and shortcuts.

        Returns:
            str: Help text.
        """
        return "\n".join([
            "Commands:",
            "  start [rx ry cx cy]  Place an order (restaurant x y, customer x y)",
            "  status  (s)          Show system funds and all riders",
            "  orders  (o)          Show all orders with statistics",
            "  riders  (r)          Show every rider's status-change log",
            "  map     (m)          Show the ASCII map",
            "  wait [n]  (w)        Advance the simulation n extra ticks (default 1)",
            "  history              Show command history",
            "  help    (h, ?)       Show this help",
            "  quit / exit  (q)     Exit the program",
            "Shortcuts: !! repeats the last command, !n repeats history entry n.",
            "Each command is followed by one simulation tick.",
        ])
