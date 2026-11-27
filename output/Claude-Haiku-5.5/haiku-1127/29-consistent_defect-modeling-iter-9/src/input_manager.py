"""Command parsing, shortcut resolution and input validation."""

import logging
from typing import List, Tuple

logger = logging.getLogger("dispatch.input")

COORD_MIN = 0
COORD_MAX = 1000
COMMANDS = ("start", "status", "orders", "riders", "map", "tick",
            "save", "history", "help", "quit", "exit")
SHORTCUTS = {
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
}


class InputError(ValueError):
    """Raised when user input is malformed or out of range."""


class InputManager:
    """Reads, records and validates user commands."""

    def __init__(self) -> None:
        """Create an input manager with empty command history."""
        self.command_history: List[str] = []

    def read_command(self, prompt: str = "dispatch> ") -> str:
        """Read one line from the user, supporting '!!' to repeat the last command.

        Args:
            prompt: Prompt text.

        Returns:
            The stripped command line (may be empty).

        Raises:
            InputError: If '!!' is used with empty history.
        """
        raw = input(prompt).strip()
        if raw == "!!":
            if not self.command_history:
                raise InputError("No previous command to repeat.")
            raw = self.command_history[-1]
            print(f"Repeating: {raw}")
        if raw:
            self.command_history.append(raw)
        return raw

    @staticmethod
    def parse_command(text: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command and arguments.

        Args:
            text: Raw command line.

        Returns:
            Tuple (command, args). Command is "" for blank input.

        Raises:
            InputError: If the command is unknown.
        """
        parts = text.split()
        if not parts:
            return "", []
        word = parts[0].lower()
        word = SHORTCUTS.get(word, word)
        if word not in COMMANDS:
            raise InputError(f"Unknown command '{parts[0]}'. Type 'help' for the command list.")
        return word, parts[1:]

    @staticmethod
    def parse_coordinates(tokens: List[str]) -> List[int]:
        """Validate exactly four integer coordinates in the range 0-1000.

        Commas are accepted as separators.

        Args:
            tokens: Tokens such as ["120", "230", "700", "810"].

        Returns:
            List [restaurant_x, restaurant_y, customer_x, customer_y].

        Raises:
            InputError: On wrong count, non-integer or out-of-range values.
        """
        text = " ".join(tokens).replace(",", " ")
        parts = text.split()
        if len(parts) != 4:
            raise InputError("Expected 4 integer coordinates: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values: List[int] = []
        for part in parts:
            try:
                value = int(part)
            except ValueError:
                raise InputError(f"'{part}' is not an integer.") from None
            if not COORD_MIN <= value <= COORD_MAX:
                raise InputError(f"Coordinate {value} is out of range "
                                 f"{COORD_MIN}-{COORD_MAX}.")
            values.append(value)
        return values

    @staticmethod
    def parse_positive_int(tokens: List[str], default: int, low: int, high: int) -> int:
        """Parse an optional integer argument within a range.

        Args:
            tokens: Argument tokens (may be empty).
            default: Value used when no token is given.
            low: Minimum allowed value.
            high: Maximum allowed value.

        Returns:
            Parsed integer.

        Raises:
            InputError: If the token is not an integer or out of range.
        """
        if not tokens:
            return default
        try:
            value = int(tokens[0])
        except ValueError:
            raise InputError(f"'{tokens[0]}' is not an integer.") from None
        if not low <= value <= high:
            raise InputError(f"Value {value} must be between {low} and {high}.")
        return value
