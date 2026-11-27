"""Input parsing and validation."""

import re

ALIASES = {"s": "status", "o": "orders", "r": "riders", "q": "quit",
           "exit": "quit", "h": "help", "?": "help", "t": "tick",
           "st": "start"}


class InputManager:
    """Parses commands and coordinates."""

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        parts = line.strip().split(None, 1)
        if not parts:
            return None, ""
        self.history.append(line.strip())
        cmd = parts[0].lower()
        return ALIASES.get(cmd, cmd), parts[1] if len(parts) > 1 else ""

    @staticmethod
    def parse_coords(text):
        """Return four ints in 0..800 or raise ValueError."""
        tokens = [t for t in re.split(r"[\s,\[\]]+", text) if t]
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: rx ry cx cy")
        vals = []
        for t in tokens:
            try:
                vals.append(int(t))
            except ValueError:
                raise ValueError("'%s' is not an integer" % t)
        for v in vals:
            if not 0 <= v <= 800:
                raise ValueError("Coordinate %d out of range 0-800" % v)
        return vals
