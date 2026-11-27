"""Command parsing, shortcut expansion, history and input validation."""

try:
    import readline  # noqa: F401  (enables arrow-key history where available)
except ImportError:  # pragma: no cover - platform dependent
    readline = None

from order_model import MAP_SIZE

COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "tick": "tick", "t": "tick",
    "map": "map", "m": "map",
    "save": "save", "w": "save",
    "history": "history", "hist": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}


class InputManager:
    """Parses user commands and validates coordinate input."""

    def __init__(self):
        """Create an input manager with an empty command history."""
        self._history = []

    @property
    def history(self):
        """Return a copy of the executed command history."""
        return list(self._history)

    def read_line(self, prompt="dispatch> "):
        """Read one raw line from standard input.

        Args:
            prompt: Prompt string displayed to the user.

        Returns:
            The stripped input line (may be empty).

        Raises:
            EOFError: At end of input.
            KeyboardInterrupt: If the user interrupts.
        """
        return input(prompt).strip()

    def expand(self, line):
        """Expand history shortcuts (``!!`` and ``!n``).

        Args:
            line: Raw command line.

        Returns:
            The expanded command line.

        Raises:
            ValueError: If the history reference is invalid.
        """
        stripped = line.strip()
        if not stripped.startswith("!"):
            return stripped
        if not self._history:
            raise ValueError("no command history available")
        if stripped == "!!":
            return self._history[-1]
        try:
            index = int(stripped[1:])
        except ValueError:
            raise ValueError(f"invalid history reference '{stripped}'") from None
        if not 1 <= index <= len(self._history):
            raise ValueError(f"history entry {index} does not exist")
        return self._history[index - 1]

    def record(self, line):
        """Store an executed command in the history.

        Args:
            line: Expanded command line.
        """
        if line:
            self._history.append(line)

    @staticmethod
    def parse(line):
        """Split a command line into a canonical command name and arguments.

        Args:
            line: Expanded command line.

        Returns:
            Tuple ``(name, args)``; ``name`` is None for unknown commands.
        """
        tokens = line.split()
        if not tokens:
            return None, []
        name = COMMAND_ALIASES.get(tokens[0].lower())
        return name, tokens[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Parse four integer coordinates from command tokens.

        Accepts spaces or commas as separators.

        Args:
            tokens: Iterable of string tokens.

        Returns:
            List of four validated integers
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the count, type or range of values is invalid.
        """
        text = " ".join(tokens).replace(",", " ")
        parts = text.split()
        if len(parts) != 4:
            raise ValueError(
                f"expected 4 integers (restaurant_x restaurant_y customer_x customer_y), got {len(parts)}"
            )
        values = []
        for part in parts:
            try:
                value = int(part)
            except ValueError:
                raise ValueError(f"'{part}' is not an integer") from None
            if not 0 <= value <= MAP_SIZE:
                raise ValueError(f"coordinate {value} out of range 0-{MAP_SIZE}")
            values.append(value)
        return values

    @staticmethod
    def parse_positive_int(tokens, default, maximum):
        """Parse an optional positive integer argument.

        Args:
            tokens: Argument tokens.
            default: Value used when no argument is given.
            maximum: Largest accepted value.

        Returns:
            The parsed integer.

        Raises:
            ValueError: If the value is not an integer within 1..maximum.
        """
        if not tokens:
            return default
        try:
            value = int(tokens[0])
        except ValueError:
            raise ValueError(f"'{tokens[0]}' is not an integer") from None
        if not 1 <= value <= maximum:
            raise ValueError(f"value must be between 1 and {maximum}")
        return value
