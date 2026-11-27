"""Command parsing, shortcut handling, command history and input validation."""

import logging
from dataclasses import dataclass, field
from typing import Callable, List

from config import MAP_SIZE

try:  # Enables line editing and arrow-key history where available.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

logger = logging.getLogger(__name__)

COMMANDS = {
    "start", "status", "orders", "riders", "map", "tick",
    "history", "save", "help", "quit", "exit",
}
SHORTCUTS = {
    "n": "start", "s": "status", "o": "orders", "r": "riders",
    "m": "map", "t": "tick", "l": "history", "w": "save",
    "h": "help", "?": "help", "q": "quit", "x": "exit",
}
COORDINATE_LABELS = ["restaurant x", "restaurant y", "customer x", "customer y"]
MAX_TICK_BATCH = 1000


class CommandError(Exception):
    """Raised for malformed or invalid user input."""


@dataclass
class Command:
    """A parsed user command.

    Attributes:
        name: Canonical command name.
        arguments: Integer arguments (coordinates or tick count).
        raw_args: The original argument tokens.
    """

    name: str
    arguments: List[int] = field(default_factory=list)
    raw_args: List[str] = field(default_factory=list)


def parse_coordinate(token: str, label: str) -> int:
    """Convert a token to a coordinate integer within the map range.

    Args:
        token: Text entered by the user.
        label: Name of the coordinate used in error messages.

    Returns:
        The integer coordinate.

    Raises:
        CommandError: If the token is not an integer or is out of range.
    """
    try:
        value = int(token)
    except ValueError:
        raise CommandError(f"{label} must be an integer, got '{token}'.") from None
    if not 0 <= value <= MAP_SIZE:
        raise CommandError(f"{label} must be between 0 and {MAP_SIZE}, got {value}.")
    return value


class InputManager:
    """Reads and parses user commands.

    Attributes:
        command_history: Every non-empty line entered, in order.
    """

    def __init__(self, input_func: Callable[[str], str] = input) -> None:
        """Create an input manager.

        Args:
            input_func: Function used to read a line (injectable for testing).
        """
        self.command_history: List[str] = []
        self._input = input_func

    def read_line(self, prompt: str = "> ") -> str:
        """Read one line, expanding ``!!`` to the previous command.

        Returns:
            The stripped line (possibly empty).

        Raises:
            CommandError: If ``!!`` is used with an empty history.
        """
        line = self._input(prompt).strip()
        if line == "!!":
            if not self.command_history:
                raise CommandError("No previous command to repeat.")
            line = self.command_history[-1]
            print(f"Repeating: {line}")
        if line:
            self.command_history.append(line)
        return line

    def parse(self, line: str) -> Command:
        """Parse a command line into a ``Command``.

        Args:
            line: The raw command line.

        Returns:
            The parsed ``Command``.

        Raises:
            CommandError: If the command is unknown or its arguments are invalid.
        """
        tokens = line.split()
        if not tokens:
            raise CommandError("Empty command.")
        token = tokens[0].lower()
        name = SHORTCUTS.get(token, token)
        if name not in COMMANDS:
            raise CommandError(f"Unknown command '{tokens[0]}'. Type 'help' for a list.")

        args = tokens[1:]
        arguments: List[int] = []
        if name == "start":
            if args and len(args) != 4:
                raise CommandError("start expects 4 integers: restaurant_x restaurant_y "
                                   "customer_x customer_y (or no arguments to be prompted).")
            arguments = [parse_coordinate(t, COORDINATE_LABELS[i]) for i, t in enumerate(args)]
        elif name == "tick" and args:
            try:
                count = int(args[0])
            except ValueError:
                raise CommandError(f"tick count must be an integer, got '{args[0]}'.") from None
            if not 1 <= count <= MAX_TICK_BATCH:
                raise CommandError(f"tick count must be between 1 and {MAX_TICK_BATCH}.")
            arguments = [count]
        return Command(name=name, arguments=arguments, raw_args=args)

    def ask_coordinates(self) -> List[int]:
        """Prompt for the four order coordinates, re-prompting on invalid input.

        Returns:
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.
        """
        values: List[int] = []
        for label in COORDINATE_LABELS:
            while True:
                raw = self._input(f"  {label} (0-{MAP_SIZE}): ").strip()
                try:
                    values.append(parse_coordinate(raw, label))
                    break
                except CommandError as exc:
                    print(f"Error: {exc}")
        return values
