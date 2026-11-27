"""Command parsing, shortcut resolution and input validation."""

from typing import Callable, List, Optional, Sequence, Tuple

from config import MAP_SIZE, is_valid_coordinate

COMMANDS = ("start", "status", "orders", "riders", "map", "tick",
            "history", "help", "quit")

COMMAND_ALIASES = {
    "n": "start",
    "s": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "quit",
    "exit": "quit",
}

MAX_TICKS_PER_COMMAND = 1000


class InputError(ValueError):
    """Raised for malformed user input or unknown commands."""


class InputManager:
    """Read and validate user commands and order coordinates.

    Attributes:
        history: Every raw line entered by the user, in order.
    """

    def __init__(self, input_func: Callable[[str], str] = input) -> None:
        """Create the manager.

        Args:
            input_func: Function used to read a line (injectable for tests).
        """
        self._input = input_func
        self.history: List[str] = []

    def read_line(self, prompt: str = "dispatch> ") -> str:
        """Read one line from the user and record it in the history."""
        line = self._input(prompt)
        self.history.append(line.strip())
        return line.strip()

    def parse_command(self, line: str) -> Tuple[Optional[str], List[str]]:
        """Split a raw line into a canonical command and its arguments.

        Args:
            line: Raw user input.

        Returns:
            ``(command, args)``; ``command`` is None for a blank line.

        Raises:
            InputError: If the command is unknown.
        """
        tokens = line.strip().split()
        if not tokens:
            return None, []
        word = tokens[0].lower()
        command = COMMAND_ALIASES.get(word, word)
        if command not in COMMANDS:
            raise InputError(f"unknown command '{tokens[0]}'. Type 'help' for the command list.")
        return command, tokens[1:]

    @staticmethod
    def parse_coordinates(text: str):
        """Parse ``restaurant_x restaurant_y customer_x customer_y``.

        Commas or spaces may separate the values.

        Args:
            text: Raw coordinate text.

        Returns:
            ``((rx, ry), (cx, cy))``.

        Raises:
            InputError: On wrong count, non-integer or out-of-range values.
        """
        tokens = text.replace(",", " ").split()
        if len(tokens) != 4:
            raise InputError(f"expected four integers, got {len(tokens)}. "
                             "Format: restaurant_x restaurant_y customer_x customer_y")
        values: List[int] = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise InputError(f"'{token}' is not an integer")
            if not is_valid_coordinate(value):
                raise InputError(f"coordinate {value} is outside the range 0-{MAP_SIZE}")
            values.append(value)
        return (values[0], values[1]), (values[2], values[3])

    def prompt_order(self):
        """Prompt repeatedly for order coordinates.

        Returns:
            ``((rx, ry), (cx, cy))`` or None if the user cancels.
        """
        while True:
            text = self._input("Enter restaurant x y and customer x y (or 'cancel'): ")
            self.history.append(text.strip())
            if text.strip().lower() in ("", "cancel", "c"):
                return None
            try:
                return self.parse_coordinates(text)
            except InputError as exc:
                print(f"Invalid input: {exc}. Please try again.")

    @staticmethod
    def parse_tick_count(args: Sequence[str]) -> int:
        """Parse the optional step count for the ``tick`` command.

        Raises:
            InputError: If the value is not an integer between 1 and 1000.
        """
        if not args:
            return 1
        try:
            steps = int(args[0])
        except ValueError:
            raise InputError(f"'{args[0]}' is not an integer tick count")
        if not 1 <= steps <= MAX_TICKS_PER_COMMAND:
            raise InputError(f"tick count must be between 1 and {MAX_TICKS_PER_COMMAND}")
        return steps
