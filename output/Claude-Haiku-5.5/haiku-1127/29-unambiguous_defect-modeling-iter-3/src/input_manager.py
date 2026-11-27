"""Command parsing, shortcut expansion and input validation."""

import logging

from grid import MAP_SIZE

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "tick": "tick", "t": "tick",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "history": "history", "hist": "history",
    "save": "save",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}

COORDINATE_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")
MAX_HISTORY = 100


class CommandError(Exception):
    """Raised for unknown commands and invalid command arguments."""


class InputManager:
    """Parses user input lines into commands.

    Attributes:
        command_history (list[str]): Previously accepted command lines.
    """

    def __init__(self, max_history=MAX_HISTORY):
        """Create an input manager.

        Args:
            max_history: Maximum number of history entries kept.
        """
        self.command_history = []
        self.max_history = max_history

    def expand(self, line):
        """Expand history shortcuts ("!!" and "!n") into the stored command.

        Args:
            line: Raw input line.

        Returns:
            str: The stripped or expanded command text.

        Raises:
            CommandError: If the referenced history entry does not exist.
        """
        text = line.strip()
        if text == "!!":
            if not self.command_history:
                raise CommandError("No previous command to repeat.")
            return self.command_history[-1]
        if text.startswith("!") and text[1:].isdigit():
            index = int(text[1:])
            if not 1 <= index <= len(self.command_history):
                raise CommandError("No history entry %d." % index)
            return self.command_history[index - 1]
        return text

    def record(self, text):
        """Append a command line to the history, trimming old entries.

        Args:
            text: Command text to store.
        """
        self.command_history.append(text)
        if len(self.command_history) > self.max_history:
            del self.command_history[:len(self.command_history) - self.max_history]

    def parse(self, line):
        """Parse an input line into a command name and argument tokens.

        Args:
            line: Raw input line.

        Returns:
            tuple: (command, args) where command is None for an empty line.

        Raises:
            CommandError: If the command is unknown.
        """
        text = self.expand(line)
        if not text:
            return None, []
        parts = text.split()
        command = COMMAND_ALIASES.get(parts[0].lower())
        if command is None:
            raise CommandError("Unknown command '%s'. Type 'help' for a list of commands."
                               % parts[0])
        self.record(text)
        return command, parts[1:]

    @staticmethod
    def validate_coordinate(text, label):
        """Validate one coordinate given as text.

        Args:
            text: Input value, which must be an integer string.
            label: Name used in error messages.

        Returns:
            int: Validated coordinate in 0-800.

        Raises:
            CommandError: If the value is not an integer or is out of range.
        """
        try:
            value = int(str(text).strip())
        except ValueError:
            raise CommandError("%s must be an integer, got '%s'." % (label, text))
        if not 0 <= value <= MAP_SIZE:
            raise CommandError("%s must be between 0 and %d, got %d."
                               % (label, MAP_SIZE, value))
        return value

    def parse_coordinates(self, tokens):
        """Validate four inline coordinate tokens.

        Args:
            tokens: List of four strings: restaurant x, y, customer x, y.

        Returns:
            list[int]: Four validated integers.

        Raises:
            CommandError: If the token count or any value is invalid.
        """
        if len(tokens) != 4:
            raise CommandError("start needs four integers: restaurant_x restaurant_y "
                               "customer_x customer_y (got %d)." % len(tokens))
        return [self.validate_coordinate(tok, label)
                for tok, label in zip(tokens, COORDINATE_LABELS)]

    def prompt_coordinates(self, reader=input):
        """Interactively ask for the four coordinates, re-prompting on errors.

        Args:
            reader: Callable used to read a line, e.g. ``input``.

        Returns:
            list[int]: Four validated integers.
        """
        values = []
        for label in COORDINATE_LABELS:
            while True:
                raw = reader("  %s (0-%d): " % (label, MAP_SIZE))
                try:
                    values.append(self.validate_coordinate(raw, label))
                    break
                except CommandError as exc:
                    print("Error: %s" % exc)
        return values
