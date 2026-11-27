"""Command parsing and input validation."""

import logging

logger = logging.getLogger(__name__)

try:  # optional, not available on Windows
    import readline  # noqa: F401
    _HAS_READLINE = True
except ImportError:  # pragma: no cover
    _HAS_READLINE = False

SHORTCUTS = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "hist": "history",
    "q": "quit",
    "exit": "quit",
}

COMMANDS = {"start", "status", "orders", "riders", "map", "tick", "run",
            "help", "history", "save", "quit"}

MAX_HISTORY = 1000


class InputManager:
    """Reads commands, keeps history and validates input."""

    def __init__(self):
        self.history = []

    def read(self, prompt="> "):
        """Read a line from the user (raises EOFError at end of input)."""
        return input(prompt)

    def add_history(self, line):
        self.history.append(line)
        if len(self.history) > MAX_HISTORY:
            del self.history[0]

    def parse_command(self, line):
        """Return (command, args). Unknown commands return their raw name.

        Supports shortcuts and '!!' to repeat the previous command.
        """
        line = (line or "").strip()
        if line == "!!":
            if not self.history:
                return "", []
            line = self.history[-1]
        if not line:
            return "", []
        self.add_history(line)
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        rest = parts[1] if len(parts) > 1 else ""
        args = rest.replace(",", " ").replace("[", " ").replace("]", " ").split()
        return cmd, args

    @staticmethod
    def parse_coordinates(data):
        """Validate and return four integer coordinates within 0..800.

        ``data`` may be a string ("100 200 300 400" or "[100,200,300,400]")
        or a sequence. Raises ValueError with a descriptive message.
        """
        if isinstance(data, str):
            tokens = data.replace(",", " ").replace("[", " ").replace("]", " ").split()
        else:
            try:
                tokens = list(data)
            except TypeError:
                raise ValueError("Coordinates must be four integers.")
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y customer_x customer_y "
                             "(got %d values)." % len(tokens))
        values = []
        for tok in tokens:
            if isinstance(tok, bool):
                raise ValueError("Invalid coordinate %r: must be an integer." % (tok,))
            if isinstance(tok, int):
                value = tok
            else:
                try:
                    value = int(str(tok).strip())
                except ValueError:
                    raise ValueError("Invalid coordinate %r: must be an integer." % (tok,))
            if not 0 <= value <= 800:
                raise ValueError("Coordinate %d out of range (0-800)." % value)
            values.append(value)
        return values

    @staticmethod
    def parse_positive_int(token, default=1, maximum=100000):
        """Parse a positive integer argument (e.g. tick count)."""
        if token is None:
            return default
        try:
            value = int(token)
        except ValueError:
            raise ValueError("Expected a positive integer, got %r." % token)
        if value < 1 or value > maximum:
            raise ValueError("Value must be between 1 and %d." % maximum)
        return value
