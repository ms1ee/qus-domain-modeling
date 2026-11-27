"""Command parsing, input validation and command history.

Supports full command names, short aliases, ``!!`` to repeat the last
command and ``!n`` to repeat history entry n.
"""

import logging

from config import COORD_MAX, COORD_MIN, HISTORY_SIZE

try:  # Enables line editing and arrow-key history on supported platforms.
    import readline  # noqa: F401  pylint: disable=unused-import
except ImportError:  # pragma: no cover - platform dependent
    readline = None

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "start": "start", "s": "start", "order": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "save": "save",
    "history": "history", "hist": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "q": "quit", "exit": "quit",
}

COORD_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")


def validate_coordinates(values):
    """Check that coordinates are integers within the map range.

    Args:
        values: Sequence of four integers.

    Raises:
        ValueError: If any value is outside 0-800.
    """
    for label, value in zip(COORD_LABELS, values):
        if not COORD_MIN <= value <= COORD_MAX:
            raise ValueError(f"{label} {value} is outside the range "
                             f"{COORD_MIN}-{COORD_MAX}")


class InputManager:
    """Reads, parses and validates user commands.

    Attributes:
        history: List of previously entered command lines.
    """

    def __init__(self, reader=input):
        """Create an input manager.

        Args:
            reader: Callable used to read a line (defaults to ``input``).
        """
        self.history = []
        self._reader = reader

    def read_line(self, prompt="dispatch> "):
        """Read one line, expanding history shortcuts and recording it.

        Args:
            prompt: Prompt text.

        Returns:
            The stripped command line (empty string for blank input).

        Raises:
            EOFError: If the input stream is closed.
            ValueError: If a history shortcut refers to a missing entry.
        """
        line = self._reader(prompt).strip()
        if not line:
            return ""
        if line == "!!":
            if not self.history:
                raise ValueError("no previous command in history")
            line = self.history[-1]
        elif line.startswith("!") and line[1:].isdigit():
            index = int(line[1:])
            if not 1 <= index <= len(self.history):
                raise ValueError(f"no history entry {index}")
            line = self.history[index - 1]
        self._remember(line)
        return line

    def _remember(self, line):
        """Append a command line to history, trimming to HISTORY_SIZE.

        Args:
            line: Command line to store.
        """
        self.history.append(line)
        if len(self.history) > HISTORY_SIZE:
            del self.history[0]

    @staticmethod
    def parse(line):
        """Split a command line into a canonical command and arguments.

        Args:
            line: Non-empty command line.

        Returns:
            Tuple ``(command, args)`` where command is the canonical name.

        Raises:
            ValueError: If the command is unknown.
        """
        tokens = line.split()
        name = tokens[0].lower()
        command = COMMAND_ALIASES.get(name)
        if command is None:
            raise ValueError(f"unknown command '{name}'. "
                             "Type 'help' for a list of commands.")
        return command, tokens[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Convert four tokens into validated integer coordinates.

        Args:
            tokens: List of string tokens.

        Returns:
            List of four integers.

        Raises:
            ValueError: If the count, type or range is wrong.
        """
        if len(tokens) != 4:
            raise ValueError("expected four integer coordinates: "
                             "restaurant_x restaurant_y customer_x "
                             "customer_y")
        values = []
        for label, token in zip(COORD_LABELS, tokens):
            try:
                values.append(int(token))
            except ValueError:
                raise ValueError(f"{label} must be an integer, "
                                 f"got '{token}'") from None
        validate_coordinates(values)
        return values

    def prompt_coordinates(self, attempts=3):
        """Ask the user for four coordinates, retrying on invalid input.

        Args:
            attempts: Maximum number of tries.

        Returns:
            List of four validated integers.

        Raises:
            ValueError: If all attempts fail.
        """
        for _ in range(attempts):
            tokens = self.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y: "
            ).split()
            try:
                return self.parse_coordinates(tokens)
            except ValueError as exc:
                print(f"Invalid input: {exc}")
        raise ValueError("too many invalid attempts; order cancelled")
