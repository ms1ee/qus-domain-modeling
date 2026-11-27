"""Command parsing and input validation."""

import re

ALIASES = {
    "s": "start", "start": "start",
    "st": "status", "status": "status",
    "o": "orders", "orders": "orders",
    "r": "riders", "riders": "riders",
    "m": "map", "map": "map",
    "n": "run", "next": "run", "run": "run", "tick": "run",
    "h": "help", "?": "help", "help": "help",
    "hist": "history", "history": "history",
    "save": "save", "load": "load",
    "q": "quit", "quit": "quit", "exit": "quit",
}

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] (s)  place an order (coords 0-800)
  status (st)              system funds and rider states
  orders (o)               all orders
  riders [id] (r)          rider status-change history
  map (m)                  ASCII map
  run [n] (n/next)         advance simulation n ticks (default 1)
  save [file] / load [file]  persist / restore state (JSON)
  history (hist)           command history
  help (h, ?)              this help
  quit / exit (q)          leave the program
Each command (or empty line) also advances the simulation by one tick."""


class InputManager:
    """Parses commands and validates coordinate input."""

    def __init__(self):
        self.command_history = []
        try:  # command history / line editing where available
            import readline  # noqa: F401
            self.readline = readline
        except ImportError:  # pragma: no cover
            self.readline = None

    def parse(self, line):
        """Return (command, args) for a raw input line."""
        line = (line or "").strip()
        if not line:
            return "", []
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        parts = line.split(None, 1)
        word = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        cmd = ALIASES.get(word, word)
        return cmd, rest

    @staticmethod
    def parse_coordinates(text):
        """Parse four integer coordinates in range 0-800.

        Accepts formats like ``[100, 200, 300, 400]`` or ``100 200 300 400``.
        Raises ValueError with a descriptive message on invalid input.
        """
        cleaned = re.sub(r"[\[\]\(\),]", " ", text or "")
        tokens = cleaned.split()
        if len(tokens) != 4:
            raise ValueError("Please enter exactly 4 coordinates: "
                             "restaurant_x restaurant_y customer_x customer_y")
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
        """Parse a positive integer, returning ``default`` for empty input."""
        text = (text or "").strip()
        if not text:
            return default
        v = int(text)
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
