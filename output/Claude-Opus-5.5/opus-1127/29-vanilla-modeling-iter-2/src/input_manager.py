"""Command parsing and input validation."""

import re

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "m": "map", "t": "tick", "h": "help", "?": "help", "q": "quit",
    "exit": "quit", "hist": "history",
}

COMMANDS = ("start", "status", "orders", "riders", "map", "tick",
            "save", "load", "history", "help", "quit")


class InputError(ValueError):
    """Raised for invalid user input."""


class InputManager:
    """Parses commands, validates coordinates and keeps command history."""

    def __init__(self):
        self.command_history = []

    def parse_command(self, line):
        """Return ``(command, args)`` from a raw input line."""
        line = (line or "").strip()
        if not line:
            return "", []
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        args = parts[1] if len(parts) > 1 else ""
        return cmd, args

    @staticmethod
    def parse_coordinates(text):
        """Parse and validate ``[rx, ry, cx, cy]`` coordinates (0..800)."""
        tokens = [t for t in re.split(r"[\s,\[\]()]+", text or "") if t]
        if len(tokens) != 4:
            raise InputError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y (got %d values)" % len(tokens))
        values = []
        for tok in tokens:
            try:
                v = int(tok)
            except ValueError:
                raise InputError("'%s' is not an integer" % tok)
            if not 0 <= v <= 800:
                raise InputError("Coordinate %d out of range 0-800" % v)
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(text, default=1):
        """Parse a positive integer argument."""
        text = (text or "").strip()
        if not text:
            return default
        try:
            v = int(text)
        except ValueError:
            raise InputError("'%s' is not an integer" % text)
        if v < 1 or v > 100000:
            raise InputError("Value must be between 1 and 100000")
        return v
