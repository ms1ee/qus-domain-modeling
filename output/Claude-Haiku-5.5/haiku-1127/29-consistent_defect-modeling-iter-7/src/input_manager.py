"""Command parsing, shortcuts, history and input validation."""

import re
from typing import List, Tuple

COORDINATE_LABELS = (
    "restaurant x",
    "restaurant y",
    "customer x",
    "customer y",
)

COMMAND_ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "hist": "history",
    "?": "help",
    "h": "help",
    "q": "quit",
    "x": "quit",
    "exit": "quit",
}

_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")


class InputError(ValueError):
    """Raised when user input cannot be accepted."""


class InputManager:
    """Parses commands and validates user-supplied values.

    Attributes:
        command_history: Previously executed commands, oldest first.
        min_coordinate: Smallest accepted coordinate.
        max_coordinate: Largest accepted coordinate.
    """

    def __init__(self, min_coordinate: int = 0, max_coordinate: int = 800,
                 history_limit: int = 200) -> None:
        """Create the input manager.

        Args:
            min_coordinate: Smallest accepted coordinate.
            max_coordinate: Largest accepted coordinate.
            history_limit: Maximum number of remembered commands.
        """
        self.command_history: List[str] = []
        self.min_coordinate = min_coordinate
        self.max_coordinate = max_coordinate
        self.history_limit = history_limit

    def resolve(self, line: str) -> str:
        """Expand history shortcuts (``!!`` and ``!n``).

        Args:
            line: Raw user input.

        Returns:
            The command text to execute.

        Raises:
            InputError: If the referenced history entry does not exist.
        """
        text = line.strip()
        if text == "!!":
            if not self.command_history:
                raise InputError("no previous command to repeat")
            return self.command_history[-1]
        if text.startswith("!") and text[1:].isdigit():
            index = int(text[1:])
            if not 1 <= index <= len(self.command_history):
                raise InputError(f"no history entry #{index}")
            return self.command_history[index - 1]
        return text

    def record(self, line: str) -> None:
        """Append a command to the history, trimming old entries."""
        if not line:
            return
        self.command_history.append(line)
        overflow = len(self.command_history) - self.history_limit
        if overflow > 0:
            del self.command_history[:overflow]

    @staticmethod
    def parse_command(text: str) -> Tuple[str, List[str]]:
        """Split a command line into a lower-case name and its arguments.

        Args:
            text: Command text.

        Returns:
            Tuple ``(name, args)``; name is "" for blank input.
        """
        parts = text.split()
        if not parts:
            return "", []
        name = parts[0].lower()
        return COMMAND_ALIASES.get(name, name), parts[1:]

    def parse_coordinates(self, tokens: List[str]) -> List[int]:
        """Validate four integer coordinates.

        Commas and spaces may both separate values.

        Args:
            tokens: Raw argument tokens.

        Returns:
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            InputError: On wrong count, non-integer text, or out-of-range value.
        """
        cleaned: List[str] = []
        for token in tokens:
            cleaned.extend(token.replace(",", " ").split())
        if len(cleaned) != 4:
            raise InputError(
                f"expected 4 integers (restaurant x y, customer x y), got {len(cleaned)}")

        values: List[int] = []
        for label, token in zip(COORDINATE_LABELS, cleaned):
            if not _INTEGER_PATTERN.match(token):
                raise InputError(f"{label} '{token}' is not an integer")
            value = int(token)
            if not self.min_coordinate <= value <= self.max_coordinate:
                raise InputError(
                    f"{label} {value} is out of range "
                    f"{self.min_coordinate}-{self.max_coordinate}")
            values.append(value)
        return values

    def parse_positive_int(self, tokens: List[str], default: int, maximum: int) -> int:
        """Parse an optional positive integer argument.

        Args:
            tokens: Argument tokens (only the first is used).
            default: Value used when no argument is given.
            maximum: Largest accepted value.

        Returns:
            The parsed integer.

        Raises:
            InputError: If the value is not a positive integer within range.
        """
        if not tokens:
            return default
        token = tokens[0]
        if not token.isdigit() or int(token) <= 0:
            raise InputError(f"'{token}' is not a positive integer")
        value = int(token)
        if value > maximum:
            raise InputError(f"value {value} exceeds maximum {maximum}")
        return value
