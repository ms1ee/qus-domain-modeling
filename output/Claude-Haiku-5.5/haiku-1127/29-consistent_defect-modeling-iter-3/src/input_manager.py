"""Command parsing, shortcuts, history and input validation."""

import logging

from order import validate_coordinates

logger = logging.getLogger(__name__)


class CommandError(ValueError):
    """Raised when a command line cannot be parsed or validated."""


ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "w": "save",
    "h": "history",
    "?": "help",
    "q": "quit",
    "e": "exit",
}

COMMANDS = (
    "start", "status", "orders", "riders", "map", "tick",
    "save", "history", "help", "quit", "exit",
)


class InputManager:
    """Parses user command lines and keeps the command history.

    Attributes:
        command_history (list[str]): Raw command lines entered so far.
    """

    def __init__(self):
        """Create an input manager with an empty history."""
        self.command_history = []

    def parse_line(self, line):
        """Parse a raw input line into a command name and arguments.

        Shortcuts supported: single-letter aliases (see ``ALIASES``), ``!!``
        to repeat the last command and ``!n`` to repeat history entry n.

        Args:
            line: Raw text entered by the user.

        Returns:
            Tuple ``(command, args)``; ``command`` is None for empty input.

        Raises:
            CommandError: If the command is unknown or the reference invalid.
        """
        text = line.strip()
        if not text:
            return None, []
        if text == "!!":
            if not self.command_history:
                raise CommandError("No previous command in history.")
            text = self.command_history[-1]
        elif text.startswith("!") and text[1:].isdigit():
            index = int(text[1:])
            if not 1 <= index <= len(self.command_history):
                raise CommandError(f"History entry {index} does not exist.")
            text = self.command_history[index - 1]

        self.command_history.append(text)
        tokens = text.split()
        name = tokens[0].lower()
        name = ALIASES.get(name, name)
        if name not in COMMANDS:
            raise CommandError(
                f"Unknown command '{tokens[0]}'. Type 'help' for the command list."
            )
        return name, tokens[1:]

    def parse_coordinates(self, tokens):
        """Convert four command tokens into validated integer coordinates.

        Args:
            tokens: Sequence of four strings
                ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            List of four integers in the range 0-1000.

        Raises:
            CommandError: If the count is wrong or a token is not an integer.
            ValueError: If a value is out of range.
        """
        if len(tokens) != 4:
            raise CommandError(
                "start needs four integers: restaurant_x restaurant_y "
                "customer_x customer_y"
            )
        values = []
        for token in tokens:
            try:
                values.append(int(token))
            except ValueError:
                raise CommandError(f"'{token}' is not an integer.") from None
        return validate_coordinates(values)
