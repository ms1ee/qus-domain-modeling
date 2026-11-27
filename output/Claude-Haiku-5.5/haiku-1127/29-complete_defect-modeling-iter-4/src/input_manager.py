"""Command parsing, shortcuts, history and input validation."""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from grid import MAP_SIZE

logger = logging.getLogger(__name__)

COORDINATE_LABELS = ["restaurant x", "restaurant y", "customer x", "customer y"]
MAX_TICKS_PER_COMMAND = 1000
MAX_HISTORY = 500


@dataclass
class Command:
    """A parsed user command.

    Attributes:
        name: Canonical command name (e.g. "start").
        arguments: Integer arguments (coordinates or tick count).
        raw_input: The full resolved input line.
    """

    name: str
    arguments: List[int] = field(default_factory=list)
    raw_input: str = ""


class InputManager:
    """Parses and validates user input and keeps the command history."""

    COMMANDS = {"start", "status", "orders", "riders", "map", "tick",
                "save", "history", "help", "quit", "exit"}
    SHORTCUTS = {
        "s": "start", "st": "status", "o": "orders", "r": "riders",
        "m": "map", "t": "tick", "v": "save", "hi": "history",
        "h": "help", "?": "help", "q": "quit", "x": "exit",
    }

    def __init__(self) -> None:
        """Create an input manager with an empty history."""
        self.command_history: List[str] = []
        self.running: bool = True

    # ------------------------------------------------------------------
    # validation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def parse_int(token: str, label: str) -> int:
        """Convert a token to an integer with a clear error message.

        Raises:
            ValueError: If the token is not an integer.
        """
        try:
            return int(token)
        except ValueError:
            raise ValueError(f"{label} must be an integer, got '{token}'") from None

    @staticmethod
    def validate_coordinate(value: int, label: str) -> int:
        """Ensure a coordinate lies within 0-800.

        Raises:
            ValueError: If the coordinate is out of range.
        """
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"{label} must be between 0 and {MAP_SIZE}, got {value}")
        return value

    # ------------------------------------------------------------------
    # input reading and history
    # ------------------------------------------------------------------
    def read_line(self, prompt: str = "> ") -> Optional[str]:
        """Read one line from standard input.

        Returns:
            The line, or None on end-of-file or interrupt.
        """
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return None

    def resolve_history(self, line: str) -> str:
        """Expand history references such as ``!!`` and ``!3``.

        Raises:
            ValueError: If the reference is invalid.
        """
        text = line.strip()
        if not text.startswith("!"):
            return text
        body = text[1:]
        if body == "!":
            if not self.command_history:
                raise ValueError("there is no previous command to repeat")
            return self.command_history[-1]
        if body.isdigit():
            index = int(body)
            if not 1 <= index <= len(self.command_history):
                raise ValueError(f"no history entry {index}")
            return self.command_history[index - 1]
        raise ValueError("history references are '!!' or '!N'")

    def record(self, line: str) -> None:
        """Append a successfully executed command to the history."""
        self.command_history.append(line)
        if len(self.command_history) > MAX_HISTORY:
            del self.command_history[: len(self.command_history) - MAX_HISTORY]

    # ------------------------------------------------------------------
    # parsing
    # ------------------------------------------------------------------
    def parse(self, line: str) -> Command:
        """Parse and validate one command line.

        Args:
            line: Raw (already history-resolved) input line.

        Returns:
            A Command object.

        Raises:
            ValueError: With a user-facing message when the input is invalid.
        """
        text = line.strip()
        if not text:
            raise ValueError("empty command; type 'help' for a list of commands")
        tokens = text.split()
        typed = tokens[0].lower()
        name = self.SHORTCUTS.get(typed, typed)
        if name not in self.COMMANDS:
            raise ValueError(f"unknown command '{tokens[0]}'; type 'help'")

        arguments: List[int] = []
        args = tokens[1:]
        if name == "start":
            if len(args) not in (0, 4):
                raise ValueError("start takes either no arguments (interactive) or "
                                 "four coordinates: restaurant_x restaurant_y "
                                 "customer_x customer_y")
            for token, label in zip(args, COORDINATE_LABELS):
                value = self.parse_int(token, label)
                arguments.append(self.validate_coordinate(value, label))
        elif name == "tick":
            if len(args) > 1:
                raise ValueError("tick takes at most one argument (number of ticks)")
            count = self.parse_int(args[0], "tick count") if args else 1
            if not 1 <= count <= MAX_TICKS_PER_COMMAND:
                raise ValueError(
                    f"tick count must be between 1 and {MAX_TICKS_PER_COMMAND}")
            arguments.append(count)
        elif name != "save" and args:
            raise ValueError(f"'{name}' does not take arguments")

        return Command(name=name, arguments=arguments, raw_input=text)
