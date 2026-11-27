"""Command parsing and input validation."""

import re

COMMANDS = ("start", "status", "orders", "riders", "tick", "save", "load",
            "map", "history", "help", "quit", "exit")

SHORTCUTS = {
    "s": "start", "n": "start", "new": "start",
    "st": "status", "o": "orders", "r": "riders",
    "t": "tick", "m": "map", "h": "help", "?": "help",
    "q": "quit", "hist": "history",
}

MIN_COORD = 0
MAX_COORD = 1000


class InputManager:
    """Parse commands and validate coordinate input."""

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        """Return ``(command, args)``; command is None for empty input."""
        line = (line or "").strip()
        if not line:
            return None, []
        self.history.append(line)
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        args = parts[1] if len(parts) > 1 else ""
        return cmd, args

    @staticmethod
    def parse_coordinates(text):
        """Parse four integer coordinates.

        Accepts "100 200 300 400", "100,200,300,400" or
        "[100, 200, 300, 400]".  Raises ValueError with a friendly
        message on invalid input.
        """
        cleaned = re.sub(r"[\[\]\(\),]", " ", text or "")
        tokens = cleaned.split()
        if len(tokens) != 4:
            raise ValueError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for tok in tokens:
            try:
                values.append(int(tok))
            except ValueError:
                raise ValueError("'%s' is not an integer" % tok) from None
        for v in values:
            if v < MIN_COORD or v > MAX_COORD:
                raise ValueError("Coordinate %d out of range (%d-%d)"
                                 % (v, MIN_COORD, MAX_COORD))
        return values
