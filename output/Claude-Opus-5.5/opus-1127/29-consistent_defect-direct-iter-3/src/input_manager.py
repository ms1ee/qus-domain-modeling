"""Command parsing and input validation."""

import re

try:  # Command history / line editing where available.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

COMMANDS = {
    "start": "start", "s": "start", "new": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "save": "save", "load": "load",
    "history": "history", "hist": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}

MIN_COORD = 0
MAX_COORD = 1000


class InputManager:
    """Parses commands and validates user input."""

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        """Return ``(command, args)``; command is None for unknown input.

        ``!!`` repeats the last command, ``!n`` repeats history entry n.
        """
        line = (line or "").strip()
        if not line:
            return "", []
        if line.startswith("!"):
            ref = line[1:]
            if ref == "!" and self.history:
                line = self.history[-1]
            elif ref.isdigit() and 1 <= int(ref) <= len(self.history):
                line = self.history[int(ref) - 1]
            else:
                return None, [line]
        parts = line.split()
        cmd = COMMANDS.get(parts[0].lower())
        if cmd is not None:
            self.history.append(line)
            if len(self.history) > 1000:
                self.history = self.history[-1000:]
        return cmd, parts[1:]

    @staticmethod
    def parse_coordinates(text):
        """Parse four integer coordinates; raises ValueError when invalid."""
        if isinstance(text, (list, tuple)):
            tokens = [str(t) for t in text]
        else:
            cleaned = re.sub(r"[\[\]()]", " ", str(text))
            tokens = [t for t in re.split(r"[,\s]+", cleaned) if t]
        if len(tokens) != 4:
            raise ValueError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for tok in tokens:
            try:
                val = int(tok)
            except ValueError:
                raise ValueError("'{}' is not an integer".format(tok))
            if not MIN_COORD <= val <= MAX_COORD:
                raise ValueError("Coordinate {} out of range {}-{}".format(
                    val, MIN_COORD, MAX_COORD))
            values.append(val)
        return values

    @staticmethod
    def help_text():
        return ("Commands:\n"
                "  start|s [rx ry cx cy]  create an order\n"
                "  status|st              system snapshot\n"
                "  orders|o               all orders\n"
                "  riders|r               rider event logs\n"
                "  map|m                  ASCII map\n"
                "  tick|t [n]             advance n ticks\n"
                "  save|load [file]       persist / restore state (JSON)\n"
                "  history|hist, !!, !n   command history\n"
                "  quit|exit|q            exit")
