"""Command parsing and input validation."""

import re

COMMANDS = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "run": "run", "ru": "run",
    "save": "save", "load": "load",
    "history": "history", "hi": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "q": "quit", "exit": "quit",
}


class InputManager:
    """Parses commands and validates order coordinates."""

    def __init__(self):
        self.history = []
        try:
            import readline  # noqa: F401  (enables arrow-key history)
            self.readline = readline
        except ImportError:
            self.readline = None

    def parse_command(self, line):
        """Return (command, args) where command may be None/'unknown'."""
        line = (line or "").strip()
        if not line:
            return None, []
        self.history.append(line)
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        parts = line.split(None, 1)
        cmd = COMMANDS.get(parts[0].lower(), "unknown:" + parts[0])
        rest = parts[1] if len(parts) > 1 else ""
        return cmd, rest

    @staticmethod
    def parse_order_input(text):
        """Parse four integer coordinates in range 0..800.

        Accepts '[1, 2, 3, 4]', '1,2,3,4' or '1 2 3 4'.
        Raises ValueError with a friendly message on bad input.
        """
        tokens = [t for t in re.split(r"[\s,\[\]()]+", text or "") if t]
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(t)
            except ValueError:
                raise ValueError("'%s' is not an integer" % t)
            if v < 0 or v > 800:
                raise ValueError("Coordinate %d out of range 0-800" % v)
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(text, default=1):
        """Parse a positive integer argument with a default."""
        text = (text or "").strip()
        if not text:
            return default
        v = int(text)
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
