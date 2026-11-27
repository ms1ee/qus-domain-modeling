"""Input parsing and validation."""

ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
           "q": "quit", "exit": "quit", "t": "tick", "h": "history"}


class InputError(ValueError):
    """Invalid user input."""


class InputManager:
    """Parses commands and keeps history."""

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        """Return (command, args)."""
        parts = line.strip().split()
        if not parts:
            return None, []
        self.history.append(line.strip())
        cmd = parts[0].lower()
        return ALIASES.get(cmd, cmd), parts[1:]

    @staticmethod
    def parse_coords(tokens):
        """Validate four integers in 0-800."""
        if len(tokens) == 1:
            tokens = tokens[0].strip("[]").replace(",", " ").split()
        if len(tokens) != 4:
            raise InputError("Need four integers: rx ry cx cy")
        vals = []
        for t in tokens:
            t = t.strip("[],")
            try:
                v = int(t)
            except ValueError:
                raise InputError("Not an integer: %r" % t)
            if not 0 <= v <= 800:
                raise InputError("Coordinate out of range 0-800: %d" % v)
            vals.append(v)
        return vals
