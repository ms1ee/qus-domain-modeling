"""Command parsing and input validation."""

from config import MAP_SIZE

try:  # command history with arrow keys where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

SHORTCUTS = {
    "s": "start", "n": "start", "new": "start",
    "st": "status", "o": "orders", "r": "riders",
    "m": "map", "t": "tick", "h": "help", "?": "help",
    "q": "quit", "exit": "quit", "hist": "history", "sv": "save",
}

COMMANDS = ("start", "status", "orders", "riders", "map", "tick",
            "help", "history", "save", "quit")


class InputManager:
    """Reads commands, keeps history and validates user input."""

    def __init__(self):
        self.history = []

    def read(self, prompt="> "):
        """Read a line from stdin (raises EOFError on end of input)."""
        line = input(prompt)
        if line.strip():
            self.history.append(line.strip())
            if len(self.history) > 1000:
                del self.history[:-1000]
        return line

    @staticmethod
    def parse_command(line):
        """Split a line into ``(command, args)`` resolving shortcuts."""
        parts = line.replace(",", " ").split()
        if not parts:
            return "", []
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        return cmd, parts[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Validate four integer coordinates within 0-800.

        Accepts tokens such as ``["[100,", "200,", ...]`` or a single
        string.  Raises ValueError with a friendly message on bad input.
        """
        if isinstance(tokens, str):
            tokens = [tokens]
        text = " ".join(str(t) for t in tokens)
        for ch in "[](),":
            text = text.replace(ch, " ")
        parts = text.split()
        if len(parts) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y (got %d values)"
                             % len(parts))
        values = []
        for p in parts:
            try:
                v = int(p)
            except ValueError:
                raise ValueError("'%s' is not an integer" % p)
            if v < 0 or v > MAP_SIZE:
                raise ValueError("Coordinate %d out of range 0-%d"
                                 % (v, MAP_SIZE))
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(tokens, default=1, maximum=100000):
        """Parse an optional positive integer argument."""
        if not tokens:
            return default
        try:
            v = int(tokens[0])
        except ValueError:
            raise ValueError("'%s' is not an integer" % tokens[0])
        if v < 1 or v > maximum:
            raise ValueError("Value must be between 1 and %d" % maximum)
        return v
