"""Command parsing and input validation."""

SHORTCUTS = {
    "s": "start", "start": "start", "new": "start",
    "st": "status", "status": "status",
    "o": "orders", "orders": "orders",
    "r": "riders", "riders": "riders",
    "m": "map", "map": "map",
    "t": "tick", "tick": "tick", "wait": "tick", "w": "tick",
    "h": "help", "help": "help", "?": "help",
    "hist": "history", "history": "history",
    "save": "save",
    "q": "quit", "quit": "quit", "exit": "quit",
}


class InputError(ValueError):
    """Raised on invalid user input."""


class InputManager:
    """Parses commands and validates coordinates."""

    MIN_COORD = 0
    MAX_COORD = 800

    def __init__(self):
        self.history = []
        try:
            import readline  # noqa: F401  (enables arrow-key history)
            self._readline = readline
        except ImportError:  # pragma: no cover - Windows
            self._readline = None

    def parse_command(self, line):
        """Return ``(command, args)``; command is None for empty input,
        "unknown" for unrecognised commands."""
        line = (line or "").strip()
        if not line:
            return None, []
        self.history.append(line)
        parts = line.split()
        cmd = SHORTCUTS.get(parts[0].lower(), "unknown")
        return cmd, parts[1:]

    def parse_coordinates(self, tokens):
        """Validate four integer coordinates in range 0-800."""
        if isinstance(tokens, str):
            tokens = tokens.replace(",", " ").replace("[", " ") \
                .replace("]", " ").split()
        else:
            joined = " ".join(str(t) for t in tokens)
            tokens = joined.replace(",", " ").replace("[", " ") \
                .replace("]", " ").split()
        if len(tokens) != 4:
            raise InputError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for tok in tokens:
            try:
                v = int(tok)
            except ValueError:
                raise InputError("'%s' is not an integer" % tok)
            if not self.MIN_COORD <= v <= self.MAX_COORD:
                raise InputError("Coordinate %d out of range (%d-%d)"
                                 % (v, self.MIN_COORD, self.MAX_COORD))
            values.append(v)
        return values

    def parse_positive_int(self, tokens, default=1, maximum=10000):
        """Parse an optional positive integer argument."""
        if not tokens:
            return default
        try:
            v = int(tokens[0])
        except ValueError:
            raise InputError("'%s' is not an integer" % tokens[0])
        if v < 1 or v > maximum:
            raise InputError("Value must be between 1 and %d" % maximum)
        return v
