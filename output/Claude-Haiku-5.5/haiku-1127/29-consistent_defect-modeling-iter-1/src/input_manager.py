"""Command parsing, shortcut resolution and input validation."""

import re
from typing import Dict, List, Sequence, Tuple


class InputError(ValueError):
    """Raised when user input cannot be accepted."""


COMMAND_ALIASES: Dict[str, str] = {
    "start": "start",
    "s": "start",
    "status": "status",
    "st": "status",
    "orders": "orders",
    "o": "orders",
    "riders": "riders",
    "r": "riders",
    "map": "map",
    "m": "map",
    "tick": "tick",
    "t": "tick",
    "run": "run",
    "save": "save",
    "help": "help",
    "h": "help",
    "?": "help",
    "quit": "quit",
    "exit": "quit",
    "q": "quit",
}

_SPLITTER = re.compile(r"[\s,]+")
MAX_HISTORY = 100


class InputManager:
    """Parses commands and validates coordinate and count arguments.

    Attributes:
        command_history: Previously accepted command lines.
        min_coordinate: Smallest accepted coordinate value.
        max_coordinate: Largest accepted coordinate value.
    """

    def __init__(self, min_coordinate: int = 0, max_coordinate: int = 1000) -> None:
        self.command_history: List[str] = []
        self.min_coordinate = min_coordinate
        self.max_coordinate = max_coordinate

    def resolve(self, raw: str) -> Tuple[str, List[str], str]:
        """Resolve a raw input line to a command name and arguments.

        ``!!`` repeats the previous command. Shortcut keys are expanded.

        Returns:
            (command name, argument tokens, expanded command text).

        Raises:
            InputError: For empty input, unknown commands or no history.
        """
        text = raw.strip()
        if not text:
            raise InputError("Empty input. Type 'help' for commands.")
        if text == "!!":
            if not self.command_history:
                raise InputError("No previous command to repeat.")
            text = self.command_history[-1]
        tokens = [t for t in _SPLITTER.split(text) if t]
        key = tokens[0].lower()
        if key not in COMMAND_ALIASES:
            raise InputError(f"Unknown command '{tokens[0]}'. Type 'help' for the command list.")
        return COMMAND_ALIASES[key], tokens[1:], text

    def record(self, text: str) -> None:
        """Store an accepted command in the history (bounded)."""
        self.command_history.append(text)
        if len(self.command_history) > MAX_HISTORY:
            del self.command_history[0]

    def parse_coordinates(self, tokens: Sequence[str]) -> List[int]:
        """Validate four integer coordinates.

        Raises:
            InputError: If the count, type or range is invalid.
        """
        if len(tokens) != 4:
            raise InputError(
                "Expected 4 integers: restaurant_x restaurant_y customer_x customer_y."
            )
        values: List[int] = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError as exc:
                raise InputError(f"'{token}' is not an integer.") from exc
            if not self.min_coordinate <= value <= self.max_coordinate:
                raise InputError(
                    f"Coordinate {value} is out of range "
                    f"[{self.min_coordinate}, {self.max_coordinate}]."
                )
            values.append(value)
        return values

    def parse_count(self, tokens: Sequence[str], default: int = 1, limit: int = 10000) -> int:
        """Parse an optional positive tick count argument.

        Raises:
            InputError: If the argument is not a positive integer within limit.
        """
        if not tokens:
            return default
        try:
            value = int(tokens[0])
        except ValueError as exc:
            raise InputError(f"'{tokens[0]}' is not an integer.") from exc
        if value < 1 or value > limit:
            raise InputError(f"Count must be between 1 and {limit}.")
        return value
