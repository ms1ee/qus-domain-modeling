"""Command parsing, input validation, and command history."""

try:  # enables arrow-key history on platforms that provide readline
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows without pyreadline
    pass

MAP_MIN = 0
MAP_MAX = 800


class InputError(Exception):
    """Raised when user input is malformed or out of range."""


class InputManager:
    """Reads and validates user commands.

    Attributes:
        command_history (list[str]): Every non-empty command entered, in order.
    """

    ALIASES = {
        "s": "start",
        "st": "status",
        "o": "orders",
        "r": "riders",
        "m": "map",
        "t": "tick",
        "h": "help",
        "q": "quit",
        "x": "exit",
    }

    def __init__(self):
        """Create an input manager with an empty history."""
        self.command_history = []

    def read_line(self, prompt="dispatch> "):
        """Read one line from standard input with history shortcuts.

        Supported shortcuts:
            ``!!``  repeat the last command.
            ``!n``  repeat the n-th command in the history (1-based).

        Returns:
            The stripped (and possibly expanded) line.

        Raises:
            InputError: If a history shortcut cannot be resolved.
        """
        raw = input(prompt).strip()
        if raw == "!!":
            if not self.command_history:
                raise InputError("No command in history to repeat.")
            raw = self.command_history[-1]
        elif raw.startswith("!") and raw[1:].isdigit():
            index = int(raw[1:])
            if index < 1 or index > len(self.command_history):
                raise InputError(f"History entry {index} does not exist.")
            raw = self.command_history[index - 1]
        if raw:
            self.command_history.append(raw)
        return raw

    def parse_command(self, line):
        """Split a line into a command name and its arguments.

        Returns:
            Tuple ``(command_name, args)``; ``command_name`` is ``None`` for
            an empty line.
        """
        tokens = line.replace(",", " ").split()
        if not tokens:
            return None, []
        name = tokens[0].lower()
        name = self.ALIASES.get(name, name)
        return name, tokens[1:]

    def parse_coordinates(self, tokens):
        """Validate four integer coordinates in the range 0-800.

        Args:
            tokens: Sequence of strings ``[rx, ry, cx, cy]``.

        Returns:
            List of four ``int`` values.

        Raises:
            InputError: On wrong count, non-integer text, or out-of-range value.
        """
        if len(tokens) != 4:
            raise InputError(
                "Expected 4 integers: restaurant_x restaurant_y customer_x customer_y."
            )
        values = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise InputError(f"'{token}' is not an integer.") from None
            if value < MAP_MIN or value > MAP_MAX:
                raise InputError(f"Coordinate {value} is outside the range {MAP_MIN}-{MAP_MAX}.")
            values.append(value)
        return values

    def parse_int(self, tokens, default, low, high, name):
        """Parse an optional single integer argument within ``[low, high]``."""
        if not tokens:
            return default
        try:
            value = int(tokens[0])
        except ValueError:
            raise InputError(f"{name} must be an integer, got '{tokens[0]}'.") from None
        if value < low or value > high:
            raise InputError(f"{name} must be between {low} and {high}.")
        return value
