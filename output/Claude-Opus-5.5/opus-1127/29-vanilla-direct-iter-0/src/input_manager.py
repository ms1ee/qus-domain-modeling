"""Command parsing and input validation."""

import re

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "q": "quit", "exit": "quit", "m": "map", "t": "tick", "h": "help",
    "?": "help", "hist": "history",
}

COMMANDS = ("start", "status", "orders", "riders", "map", "tick", "run",
            "save", "load", "history", "help", "quit")


class InputManager:
    """Parses commands and validates coordinate input."""

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        """Return (command, args) for an input line; command may be None."""
        line = (line or "").strip()
        if not line:
            return None, []
        self.history.append(line)
        parts = line.split()
        cmd = SHORTCUTS.get(parts[0].lower(), parts[0].lower())
        return cmd, parts[1:]

    @staticmethod
    def parse_coordinates(text):
        """Parse four integer coordinates in range 0-800.

        Raises ValueError with a readable message on invalid input.
        """
        tokens = [t for t in re.split(r"[\s,\[\]()]+", (text or "").strip()) if t]
        if len(tokens) != 4:
            raise ValueError("Please enter exactly 4 coordinates: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(t)
            except ValueError:
                raise ValueError("'%s' is not an integer" % t)
            if not 0 <= v <= 800:
                raise ValueError("Coordinate %d out of range 0-800" % v)
            values.append(v)
        return values
