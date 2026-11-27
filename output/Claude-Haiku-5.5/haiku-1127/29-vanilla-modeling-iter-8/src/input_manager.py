"""Command parsing, validation and history for the command-line interface."""

import logging
import re
from typing import Callable, List, Sequence, Tuple

logger = logging.getLogger(__name__)

COORD_MIN = 0
COORD_MAX = 800

COMMAND_ALIASES = {
    "s": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
    "w": "save",
    "hist": "history",
}

KNOWN_COMMANDS = (
    "start", "status", "orders", "riders", "map", "tick",
    "save", "history", "help", "quit", "exit",
)


class InputError(ValueError):
    """Raised when user input cannot be parsed or validated."""


class InputManager:
    """Reads, expands, parses and validates user commands.

    Attributes:
        command_history: Every accepted command line, in order.
    """

    def __init__(self, reader: Callable[[str], str] = input) -> None:
        """Create an input manager.

        Args:
            reader: Callable used to read one line (defaults to ``input``).
        """
        self._reader = reader
        self.command_history: List[str] = []

    def read_line(self, prompt: str = "delivery> ") -> str:
        """Read a stripped line of user input."""
        return self._reader(prompt).strip()

    def expand_shortcut(self, line: str) -> str:
        """Expand history shortcuts '!!' and '!n'.

        Raises:
            InputError: If the referenced history entry does not exist.
        """
        if line == "!!":
            if not self.command_history:
                raise InputError("no previous command in history")
            return self.command_history[-1]
        match = re.fullmatch(r"!(\d+)", line)
        if match:
            index = int(match.group(1))
            if not 1 <= index <= len(self.command_history):
                raise InputError(f"history entry {index} does not exist")
            return self.command_history[index - 1]
        return line

    def record(self, line: str) -> None:
        """Append a command line to the history."""
        self.command_history.append(line)

    def parse_command(self, line: str) -> Tuple[str, List[str]]:
        """Split a line into a canonical command name and its arguments.

        Raises:
            InputError: If the line is empty or the command is unknown.
        """
        tokens = line.split()
        if not tokens:
            raise InputError("empty command")
        name = tokens[0].lower()
        name = COMMAND_ALIASES.get(name, name)
        if name not in KNOWN_COMMANDS:
            raise InputError(
                f"unknown command '{tokens[0]}'. Type 'help' for a list.")
        return name, tokens[1:]

    @staticmethod
    def validate_coordinates(values: Sequence[int]) -> List[int]:
        """Check that every value lies within the map range 0-800.

        Raises:
            InputError: If any value is out of range.
        """
        for value in values:
            if not COORD_MIN <= value <= COORD_MAX:
                raise InputError(
                    f"coordinate {value} out of range {COORD_MIN}-{COORD_MAX}")
        return list(values)

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Parse four integer coordinates separated by spaces or commas.

        Returns:
            [restaurant_x, restaurant_y, customer_x, customer_y]

        Raises:
            InputError: On wrong count, non-integer or out-of-range values.
        """
        normalized = " ".join(tokens).replace(",", " ").split()
        if len(normalized) != 4:
            raise InputError(
                "expected four integers: restaurant_x restaurant_y "
                "customer_x customer_y")
        values: List[int] = []
        for token in normalized:
            try:
                values.append(int(token))
            except ValueError:
                raise InputError(f"'{token}' is not an integer") from None
        return InputManager.validate_coordinates(values)

    @staticmethod
    def parse_positive_int(tokens: Sequence[str], default: int,
                           maximum: int) -> int:
        """Parse an optional positive integer argument within a bound.

        Raises:
            InputError: If the argument is not an integer in 1..maximum.
        """
        if not tokens:
            return default
        try:
            value = int(tokens[0])
        except ValueError:
            raise InputError(f"'{tokens[0]}' is not an integer") from None
        if not 1 <= value <= maximum:
            raise InputError(f"value must be between 1 and {maximum}")
        return value
