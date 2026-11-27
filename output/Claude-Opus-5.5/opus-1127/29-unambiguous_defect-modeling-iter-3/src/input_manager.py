"""Command parsing and input validation."""

import re

from grid_map import MAP_SIZE

try:  # Arrow-key history where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None


class InputError(ValueError):
    """Invalid user input."""


SHORTCUTS = {
    "start": "start", "n": "start", "1": "start", "new": "start",
    "status": "status", "s": "status", "2": "status",
    "orders": "orders", "o": "orders", "3": "orders",
    "riders": "riders", "r": "riders", "4": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick", "step": "tick",
    "run": "run",
    "save": "save",
    "history": "history", "h": "history",
    "help": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}


class InputManager:
    """Parses commands, keeps history and validates coordinates."""

    def __init__(self):
        self.command_history = []

    def expand_history(self, line):
        """Expand ``!!`` and ``!n`` history references."""
        line = line.strip()
        if line == "!!":
            if not self.command_history:
                raise InputError("No command history.")
            return self.command_history[-1]
        m = re.fullmatch(r"!(\d+)", line)
        if m:
            idx = int(m.group(1))
            if not 1 <= idx <= len(self.command_history):
                raise InputError("No such history entry: %d" % idx)
            return self.command_history[idx - 1]
        return line

    def parse_command(self, line):
        """Return (command, args). Unknown commands return (None, args)."""
        line = self.expand_history(line)
        if not line:
            return "", []
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        parts = line.replace(",", " ").split()
        cmd = SHORTCUTS.get(parts[0].lower())
        return cmd, parts[1:]

    @staticmethod
    def parse_coordinates(data):
        """Parse four integer coordinates (string or token list)."""
        if isinstance(data, str):
            tokens = re.sub(r"[\[\](),]", " ", data).split()
        else:
            tokens = []
            for t in data:
                tokens.extend(re.sub(r"[\[\](),]", " ", str(t)).split())
        if len(tokens) != 4:
            raise InputError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(t)
            except ValueError:
                raise InputError("'%s' is not an integer." % t)
            if not 0 <= v <= MAP_SIZE:
                raise InputError("Coordinate %d out of range (0-%d)." % (v, MAP_SIZE))
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(token, default):
        if token is None:
            return default
        try:
            v = int(token)
        except ValueError:
            raise InputError("'%s' is not an integer." % token)
        if v <= 0:
            raise InputError("Value must be positive.")
        return v

    def format_history(self):
        if not self.command_history:
            return "(empty history)"
        return "\n".join("%4d  %s" % (i + 1, c)
                         for i, c in enumerate(self.command_history))
