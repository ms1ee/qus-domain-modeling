"""Command parsing, history and input validation."""

import re

try:  # optional line editing / arrow-key history
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

COMMANDS = ("start", "status", "orders", "riders", "map", "step",
            "save", "load", "history", "help", "quit", "exit")

SHORTCUTS = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "n": "step",
    "h": "help",
    "?": "help",
    "hist": "history",
    "q": "quit",
}


class InputManager:
    """Parses commands, keeps command history and validates input."""

    def __init__(self, max_history=500):
        self.command_history = []
        self.max_history = max_history

    def add_history(self, line):
        """Append a line to the command history."""
        self.command_history.append(line)
        if len(self.command_history) > self.max_history:
            del self.command_history[:len(self.command_history) - self.max_history]

    def resolve(self, line):
        """Resolve a raw input line into ``(command, args)``.

        Supports shortcuts, ``!!`` (repeat last) and ``!n`` (repeat n-th).

        Raises:
            ValueError: on unknown commands or bad history references.
        """
        line = (line or "").strip()
        if not line:
            return None, []
        if line.startswith("!"):
            ref = line[1:]
            if ref == "!":
                if not self.command_history:
                    raise ValueError("No command history yet")
                line = self.command_history[-1]
            else:
                try:
                    idx = int(ref)
                    line = self.command_history[idx - 1]
                except (ValueError, IndexError):
                    raise ValueError("Invalid history reference: {}".format(line))
        parts = line.split()
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        if cmd not in COMMANDS:
            raise ValueError("Unknown command '{}'. Type 'help' for a list of commands.".format(parts[0]))
        self.add_history(line)
        return cmd, parts[1:]

    @staticmethod
    def parse_coordinates(text):
        """Parse and validate ``[res_x, res_y, cus_x, cus_y]``.

        Raises:
            ValueError: with a descriptive message on invalid input.
        """
        cleaned = re.sub(r"[\[\](),;]", " ", text or "")
        tokens = cleaned.split()
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y customer_x customer_y "
                             "(got {})".format(len(tokens)))
        values = []
        for tok in tokens:
            if not re.fullmatch(r"[+-]?\d+", tok):
                raise ValueError("'{}' is not an integer".format(tok))
            v = int(tok)
            if v < 0 or v > 800:
                raise ValueError("Coordinate {} out of range (0-800)".format(v))
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(text, default=1):
        """Parse a positive integer argument."""
        if text is None:
            return default
        if not re.fullmatch(r"\d+", str(text)) or int(text) <= 0:
            raise ValueError("'{}' is not a positive integer".format(text))
        return int(text)
