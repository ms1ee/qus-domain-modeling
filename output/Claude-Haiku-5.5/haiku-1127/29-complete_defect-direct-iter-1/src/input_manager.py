"""Command parsing, input validation and command history."""

import logging

try:  # Enables arrow-key line editing where available.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

logger = logging.getLogger(__name__)

MIN_COORD = 0
MAX_COORD = 800

COMMANDS = ("start", "status", "orders", "riders", "map", "tick",
            "save", "history", "help", "quit", "exit")

SHORTCUTS = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "v": "save",
    "h": "history",
    "?": "help",
    "q": "quit",
}


class InputManager:
    """Reads, parses and validates user commands.

    Supports shortcut keys ('s' for start, 'q' for quit, ...), history
    recall with '!!' (last command) and '!n' (n-th command), and optional
    readline support.
    """

    def __init__(self):
        """Create an input manager with an empty command history."""
        self.history = []

    def read_line(self, prompt="dispatch> "):
        """Read one command line from standard input.

        Args:
            prompt: Prompt string shown to the user.

        Returns:
            str: The command text (history references are expanded).
            Empty string for a blank line.

        Raises:
            EOFError: When input is closed.
            ValueError: If a history reference cannot be resolved.
        """
        raw = input(prompt).strip()
        if not raw:
            return ""
        if raw == "!!":
            if not self.history:
                raise ValueError("No command in history to repeat.")
            raw = self.history[-1]
        elif raw.startswith("!") and raw[1:].isdigit():
            index = int(raw[1:])
            if not 1 <= index <= len(self.history):
                raise ValueError(f"History entry {index} does not exist.")
            raw = self.history[index - 1]
        self.history.append(raw)
        return raw

    def parse(self, line):
        """Split a command line into a normalised command name and arguments.

        Args:
            line: Raw command text.

        Returns:
            tuple[str, list[str]]: (command, arguments).

        Raises:
            ValueError: If the command is unknown.
        """
        tokens = line.split()
        if not tokens:
            raise ValueError("Empty command.")
        command = tokens[0].lower()
        command = SHORTCUTS.get(command, command)
        if command not in COMMANDS:
            raise ValueError(f"Unknown command '{tokens[0]}'. Type 'help' for a list.")
        return command, tokens[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Parse and validate four integer coordinates.

        Accepts space- or comma-separated values, e.g. ``100 200 300 400``
        or ``100,200,300,400``.

        Args:
            tokens: Sequence of text tokens.

        Returns:
            list[int]: [restaurant_x, restaurant_y, customer_x, customer_y].

        Raises:
            ValueError: If the count is wrong, a value is not an integer,
                or a value is outside 0-800.
        """
        text = " ".join(tokens).replace(",", " ")
        parts = text.split()
        if len(parts) != 4:
            raise ValueError(
                "Expected 4 coordinates: restaurant_x restaurant_y "
                f"customer_x customer_y (got {len(parts)}).")
        values = []
        names = ("restaurant_x", "restaurant_y", "customer_x", "customer_y")
        for name, part in zip(names, parts):
            try:
                value = int(part)
            except ValueError as exc:
                raise ValueError(
                    f"{name} must be an integer, got '{part}'.") from exc
            if not MIN_COORD <= value <= MAX_COORD:
                raise ValueError(
                    f"{name} = {value} is out of range; use 0-{MAX_COORD}.")
            values.append(value)
        return values

    def prompt_coordinates(self):
        """Ask the user for the four order coordinates interactively.

        Returns:
            list[int]: Validated coordinates.

        Raises:
            ValueError: If the entered coordinates are invalid.
        """
        text = input("Enter restaurant_x restaurant_y customer_x customer_y: ")
        return self.parse_coordinates(text.split())
