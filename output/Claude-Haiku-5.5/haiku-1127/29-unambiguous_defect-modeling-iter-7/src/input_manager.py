"""Command parsing, validation and history for the command line interface."""

from typing import List, Tuple

from grid import MAP_SIZE

COMMAND_ALIASES = {
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
    "history": "history",
    "h": "history",
    "help": "help",
    "?": "help",
    "quit": "quit",
    "exit": "quit",
    "q": "quit",
}

MAX_TICK_STEP = 1000


class InputManager:
    """Parses user commands and validates their arguments.

    Attributes:
        command_history: Commands entered so far, oldest first.
    """

    def __init__(self) -> None:
        """Create an input manager with empty history."""
        self.command_history: List[str] = []

    def expand(self, line: str) -> str:
        """Resolve history shortcuts (``!!`` and ``!n``).

        Args:
            line: Raw user input.

        Returns:
            str: The command to execute.

        Raises:
            ValueError: If the referenced history entry does not exist.
        """
        text = line.strip()
        if text == "!!":
            if not self.command_history:
                raise ValueError("No previous command in history.")
            return self.command_history[-1]
        if text.startswith("!") and text[1:].isdigit():
            index = int(text[1:])
            if index < 1 or index > len(self.command_history):
                raise ValueError(f"History entry {index} does not exist.")
            return self.command_history[index - 1]
        return text

    def record(self, line: str) -> None:
        """Append a command to the history.

        Args:
            line: Command text.

        Returns:
            None
        """
        if line:
            self.command_history.append(line)

    def parse(self, line: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command name and arguments.

        Args:
            line: Command text.

        Returns:
            Tuple[str, List[str]]: Canonical command and argument tokens.

        Raises:
            ValueError: If the command is unknown.
        """
        tokens = line.split()
        if not tokens:
            return "", []
        word = tokens[0].lower()
        if word not in COMMAND_ALIASES:
            raise ValueError(f"Unknown command '{word}'. Type 'help' for a list of commands.")
        return COMMAND_ALIASES[word], tokens[1:]

    @staticmethod
    def parse_coordinates(tokens: List[str], expected: int = 4) -> List[int]:
        """Parse and validate integer coordinates.

        Accepts space or comma separated values, optionally wrapped in brackets.

        Args:
            tokens: Argument tokens.
            expected: Required number of values.

        Returns:
            List[int]: Validated coordinates.

        Raises:
            ValueError: If the count, type or range is wrong.
        """
        text = " ".join(tokens).replace("[", " ").replace("]", " ").replace(",", " ")
        parts = text.split()
        if len(parts) != expected:
            raise ValueError(
                f"expected {expected} integers: restaurant_x restaurant_y "
                f"customer_x customer_y (got {len(parts)})"
            )
        values = []
        for part in parts:
            try:
                value = int(part)
            except ValueError:
                raise ValueError(f"'{part}' is not an integer") from None
            if not 0 <= value <= MAP_SIZE:
                raise ValueError(f"coordinate {value} is outside the range 0-{MAP_SIZE}")
            values.append(value)
        return values

    @staticmethod
    def parse_tick_count(tokens: List[str]) -> int:
        """Parse the optional step count for the ``tick`` command.

        Args:
            tokens: Argument tokens.

        Returns:
            int: Number of ticks (default 1).

        Raises:
            ValueError: If the value is not a positive integer within limits.
        """
        if not tokens:
            return 1
        try:
            count = int(tokens[0])
        except ValueError:
            raise ValueError(f"'{tokens[0]}' is not an integer") from None
        if not 1 <= count <= MAX_TICK_STEP:
            raise ValueError(f"tick count must be between 1 and {MAX_TICK_STEP}")
        return count
