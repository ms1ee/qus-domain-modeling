"""Command parsing, coordinate validation, and command history."""

import logging
from typing import Callable, List, Optional, Tuple

try:  # readline provides line editing and history on POSIX systems
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

from path_planner import MAP_SIZE

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "start": "start",
    "a": "start",
    "status": "status",
    "s": "status",
    "orders": "orders",
    "o": "orders",
    "riders": "riders",
    "r": "riders",
    "map": "map",
    "m": "map",
    "wait": "wait",
    "w": "wait",
    "history": "history",
    "help": "help",
    "h": "help",
    "?": "help",
    "quit": "quit",
    "exit": "quit",
    "q": "quit",
}

MAX_WAIT_TICKS = 1000


class ValidationError(ValueError):
    """Raised when user input is malformed or out of range."""


class InputManager:
    """Reads user input, parses commands, and validates coordinates.

    Attributes:
        history: Non-empty command lines entered during this session.
    """

    def __init__(self, input_func: Callable[[str], str] = input) -> None:
        """Create the input manager.

        Args:
            input_func: Function used to read a line, injectable for testing.
        """
        self._input = input_func
        self.history: List[str] = []

    def read_line(self, prompt: str) -> str:
        """Read one line of input and record it in the history.

        Args:
            prompt: Prompt text shown to the user.

        Raises:
            EOFError: If input is closed.
        """
        line = self._input(prompt)
        if line.strip():
            self.history.append(line.strip())
        return line

    @staticmethod
    def parse_command(line: str) -> Optional[Tuple[str, List[str]]]:
        """Parse a command line into a canonical command name and arguments.

        Commas are treated as spaces, so ``start 100,200,300,400`` works.

        Args:
            line: Raw input line.

        Returns:
            ``(command, args)``, or None for an empty line.

        Raises:
            ValidationError: If the command is unknown.
        """
        tokens = line.replace(",", " ").split()
        if not tokens:
            return None
        word = tokens[0].lower()
        command = COMMAND_ALIASES.get(word)
        if command is None:
            raise ValidationError(f"unknown command '{tokens[0]}'. Type 'help' for the list.")
        return command, tokens[1:]

    @staticmethod
    def parse_coordinates(tokens: List[str]) -> List[int]:
        """Convert four tokens into validated integer coordinates.

        Args:
            tokens: Four string tokens.

        Returns:
            List of four integers in the range 0-800.

        Raises:
            ValidationError: If the count is wrong, a token is not an integer,
                or a value is out of range.
        """
        if len(tokens) != 4:
            raise ValidationError(f"expected 4 integers, got {len(tokens)}")
        values: List[int] = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise ValidationError(f"'{token}' is not an integer") from None
            if not 0 <= value <= MAP_SIZE:
                raise ValidationError(f"coordinate {value} is out of range 0-{MAP_SIZE}")
            values.append(value)
        return values

    def read_order_coordinates(self, args: List[str]) -> Optional[List[int]]:
        """Obtain the four order coordinates from arguments or by prompting.

        When arguments are given they are validated directly. Otherwise the user
        is prompted until the input is valid. An empty line cancels the order.

        Args:
            args: Arguments that followed the ``start`` command.

        Returns:
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``, or None if cancelled.

        Raises:
            ValidationError: If arguments were supplied and are invalid.
        """
        if args:
            return self.parse_coordinates(args)
        prompt = "Enter restaurant_x restaurant_y customer_x customer_y (0-800), blank to cancel: "
        while True:
            text = self.read_line(prompt)
            if not text.strip():
                return None
            try:
                return self.parse_coordinates(text.replace(",", " ").split())
            except ValidationError as exc:
                print(f"Invalid input: {exc}. Try again or press Enter to cancel.")

    @staticmethod
    def parse_wait_ticks(args: List[str]) -> int:
        """Parse the optional tick count of the ``wait`` command.

        Args:
            args: Command arguments; empty means one tick.

        Returns:
            Number of ticks, between 1 and 1000.

        Raises:
            ValidationError: If the value is not a valid positive integer.
        """
        if not args:
            return 1
        try:
            value = int(args[0])
        except ValueError:
            raise ValidationError(f"'{args[0]}' is not an integer") from None
        if not 1 <= value <= MAX_WAIT_TICKS:
            raise ValidationError(f"tick count must be between 1 and {MAX_WAIT_TICKS}")
        return value
