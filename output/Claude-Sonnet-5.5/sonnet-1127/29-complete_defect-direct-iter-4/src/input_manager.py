"""Command parsing and validation."""


class InputError(ValueError):
    """Invalid user input."""


class InputManager:
    """Parses commands."""

    ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
               "q": "quit", "exit": "quit", "t": "tick"}

    def __init__(self):
        self.history = []

    def parse(self, line):
        """Return (command, args)."""
        parts = line.strip().split()
        if not parts:
            raise InputError("empty command")
        self.history.append(line.strip())
        cmd = parts[0].lower()
        cmd = self.ALIASES.get(cmd, cmd)
        if cmd not in ("start", "status", "orders", "riders", "quit",
                       "tick", "history"):
            raise InputError("unknown command: %s" % parts[0])
        return cmd, parts[1:]

    @staticmethod
    def parse_coords(args):
        """Validate four integers in 0-800."""
        if len(args) != 4:
            raise InputError("need 4 integers: rx ry cx cy")
        vals = []
        for a in args:
            try:
                vals.append(int(a.strip("[],")))
            except ValueError:
                raise InputError("not an integer: %s" % a)
        for v in vals:
            if not 0 <= v <= 800:
                raise InputError("coordinate out of range 0-800: %d" % v)
        return vals
