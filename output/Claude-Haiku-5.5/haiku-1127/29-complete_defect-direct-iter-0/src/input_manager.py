"""Command parsing, shortcut resolution, history and input validation."""

import logging
import re
from typing import Callable, List, Optional, Sequence, Tuple

from grid import validate_coordinate

logger = logging.getLogger(__name__)

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
    "help": "help",
    "h": "help",
    "?": "help",
    "quit": "quit",
    "exit": "quit",
    "q": "quit",
}

COORDINATE_NAMES = (
    "restaurant x",
    "restaurant y",
    "customer x",
    "customer y",
)

_INTEGER_PATTERN = re.compile(r"[+-]?\d+")

try:  # readline is optional and only available on some platforms
    import readline  # pylint: disable=unused-import
    _READLINE = readline
except ImportError:  # pragma: no cover - platform dependent
    _READLINE = None


class InputManager:
    """Reads user commands and validates their arguments.

    Attributes:
        prompt: Text shown before each command.
        history: Previously entered commands (newest last).
    """

    def __init__(
        self,
        prompt: str = "dispatch> ",
        input_func: Callable[[str], str] = input,
    ) -> None:
        """Create the input manager.

        Args:
            prompt: Command prompt text.
            input_func: Function used to read a line (injectable for tests).
        """
        self.prompt = prompt
        self.history: List[str] = []
        self._input = input_func
        if _READLINE is not None:
            try:
                _READLINE.set_history_length(200)
            except (AttributeError, OSError):  # pragma: no cover
                pass

    def read_command(self) -> str:
        """Read one command line, handling the ``!!`` repeat shortcut.

        Returns:
            The stripped command text (may be empty).

        Raises:
            EOFError: If input is closed.
            ValueError: If ``!!`` is used with an empty history.
        """
        line = self._input(self.prompt).strip()
        if line == "!!":
            if not self.history:
                raise ValueError("no previous command to repeat")
            line = self.history[-1]
            print(f"Repeating: {line}")
        if line:
            self.history.append(line)
            if _READLINE is not None:
                try:
                    _READLINE.add_history(line)
                except (AttributeError, OSError):  # pragma: no cover
                    pass
        return line

    @staticmethod
    def parse_command(line: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command and arguments.

        Args:
            line: Raw command text.

        Returns:
            Tuple ``(command, arguments)``.

        Raises:
            ValueError: If the command is unknown.
        """
        parts = line.split()
        if not parts:
            raise ValueError("empty command")
        command = COMMAND_ALIASES.get(parts[0].lower())
        if command is None:
            raise ValueError(f"unknown command '{parts[0]}'")
        return command, parts[1:]

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Parse and validate four integer coordinates.

        Accepts whitespace, commas or brackets as separators, for example
        ``100 200 300 400`` or ``[100, 200, 300, 400]``.

        Args:
            tokens: Text pieces containing the coordinates.

        Returns:
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the count, type or range is invalid.
        """
        text = " ".join(tokens)
        for separator in "[],":
            text = text.replace(separator, " ")
        parts = text.split()
        if len(parts) != 4:
            raise ValueError(
                "expected 4 integer coordinates (restaurant x y, customer "
                f"x y), got {len(parts)} value(s)"
            )
        values: List[int] = []
        for part, name in zip(parts, COORDINATE_NAMES):
            if not _INTEGER_PATTERN.fullmatch(part):
                raise ValueError(f"{name} must be an integer, got '{part}'")
            values.append(validate_coordinate(int(part), name))
        return values

    def request_order_coordinates(self) -> Optional[List[int]]:
        """Interactively ask for order coordinates until valid or cancelled.

        Returns:
            The four validated coordinates, or None if the user cancelled
            with an empty line.
        """
        prompt = (
            "Enter restaurant x y and customer x y (0-800), blank to cancel: "
        )
        while True:
            text = self._input(prompt).strip()
            if not text:
                return None
            try:
                return self.parse_coordinates(text.split())
            except ValueError as exc:
                print(f"Invalid input: {exc}. Please try again.")
