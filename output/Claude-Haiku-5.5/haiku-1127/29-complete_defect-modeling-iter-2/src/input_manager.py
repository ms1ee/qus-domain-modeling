"""Command parsing, shortcut resolution, command history and input validation."""

from typing import List, Tuple

from settings import CONFIG

COMMANDS = (
    "start", "status", "orders", "riders", "map", "tick",
    "history", "save", "help", "quit", "exit",
)

SHORTCUTS = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "history",
    "sv": "save",
    "?": "help",
    "q": "quit",
    "x": "exit",
}

COORDINATE_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")
MAX_HISTORY = 500


class InputError(ValueError):
    """Raised when user input is malformed or out of range."""


class InputManager:
    """Reads, expands, records and parses user commands.

    Attributes:
        command_history: Accepted command lines, oldest first.
    """

    def __init__(self, prompt: str = "dispatch> ") -> None:
        self.prompt = prompt
        self.command_history: List[str] = []

    def read_line(self, prompt: str = None) -> str:
        """Read one line from standard input, stripped of whitespace.

        Raises:
            EOFError: At end of input.
        """
        return input(prompt if prompt is not None else self.prompt).strip()

    def expand_history(self, line: str) -> str:
        """Expand ``!!`` (last command) and ``!n`` (command number n).

        Raises:
            InputError: If the referenced history entry does not exist.
        """
        if line == "!!":
            if not self.command_history:
                raise InputError("no previous command in history")
            return self.command_history[-1]
        if line.startswith("!") and line[1:].isdigit():
            index = int(line[1:])
            if not 1 <= index <= len(self.command_history):
                raise InputError(f"no history entry #{index}")
            return self.command_history[index - 1]
        return line

    def record(self, line: str) -> None:
        """Append a command to the history, keeping at most MAX_HISTORY entries."""
        self.command_history.append(line)
        if len(self.command_history) > MAX_HISTORY:
            del self.command_history[: len(self.command_history) - MAX_HISTORY]

    def parse(self, line: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command name and arguments.

        Raises:
            InputError: If the line is empty or the command is unknown.
        """
        parts = line.replace(",", " ").split()
        if not parts:
            raise InputError("empty command")
        name = parts[0].lower()
        command = SHORTCUTS.get(name, name)
        if command not in COMMANDS:
            raise InputError(f"unknown command '{parts[0]}'. Type 'help' for the list.")
        return command, parts[1:]

    @staticmethod
    def parse_coordinates(tokens: List[str]) -> List[int]:
        """Validate four coordinate tokens: restaurant x/y, customer x/y.

        Raises:
            InputError: If the count, type or range is wrong.
        """
        if len(tokens) != 4:
            raise InputError(
                "expected 4 integers: restaurant_x restaurant_y customer_x customer_y "
                f"(got {len(tokens)})"
            )
        values: List[int] = []
        for label, token in zip(COORDINATE_LABELS, tokens):
            try:
                value = int(token)
            except ValueError:
                raise InputError(f"{label} must be an integer, got '{token}'") from None
            if not 0 <= value <= CONFIG["map_size"]:
                raise InputError(
                    f"{label} must be within 0-{CONFIG['map_size']}, got {value}"
                )
            values.append(value)
        return values

    @staticmethod
    def parse_tick_count(tokens: List[str], maximum: int) -> int:
        """Parse an optional positive tick count, defaulting to 1.

        Raises:
            InputError: If the value is not an integer or is out of range.
        """
        if not tokens:
            return 1
        try:
            count = int(tokens[0])
        except ValueError:
            raise InputError(f"tick count must be an integer, got '{tokens[0]}'") from None
        if not 1 <= count <= maximum:
            raise InputError(f"tick count must be between 1 and {maximum}")
        return count
