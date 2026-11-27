"""Command parsing, validation and input history."""

from typing import Callable, List, Optional, Sequence, Tuple

from config import COORD_MAX, COORD_MIN

SHORTCUTS = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "hist": "history",
    "q": "quit",
    "x": "exit",
}

COMMANDS = {
    "start", "status", "orders", "riders", "map", "tick",
    "help", "history", "save", "quit", "exit",
}


class InputManager:
    """Read raw input, record history and parse commands with validation."""

    def __init__(self, reader: Optional[Callable[[str], str]] = None) -> None:
        """Create the manager.

        Args:
            reader: Callable used to read a line of text (defaults to input).
        """
        self.command_history: List[str] = []
        self._reader = reader or input

    def read_line(self, prompt: str = "> ") -> str:
        """Read one stripped line and record non-empty entries in history."""
        line = self._reader(prompt).strip()
        if line:
            self.command_history.append(line)
        return line

    def parse_command(self, line: str) -> Tuple[str, List[str]]:
        """Split a line into a canonical command name and its arguments.

        Raises:
            ValueError: If the command is unknown.
        """
        tokens = line.split()
        if not tokens:
            raise ValueError("Empty command. Type 'help' for the command list.")
        head = tokens[0].lower()
        name = SHORTCUTS.get(head, head)
        if name not in COMMANDS:
            raise ValueError(f"Unknown command '{tokens[0]}'. Type 'help'.")
        return name, tokens[1:]

    def parse_coordinates(self, tokens: Sequence[str]) -> List[int]:
        """Validate four integer coordinates in the allowed range.

        Raises:
            ValueError: With a clear message if the input is invalid.
        """
        if len(tokens) != 4:
            raise ValueError(
                "Expected four integers: restaurant_x restaurant_y "
                "customer_x customer_y")
        values: List[int] = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise ValueError(f"'{token}' is not an integer.") from None
            if not COORD_MIN <= value <= COORD_MAX:
                raise ValueError(
                    f"Coordinate {value} is out of range "
                    f"{COORD_MIN}-{COORD_MAX}.")
            values.append(value)
        return values

    def get_history(self) -> List[str]:
        """Return a copy of the command history."""
        return list(self.command_history)
