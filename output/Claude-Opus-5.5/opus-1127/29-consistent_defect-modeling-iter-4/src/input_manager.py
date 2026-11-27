"""Command parsing and input validation."""

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "q": "quit", "h": "help", "?": "help", "m": "map", "t": "tick",
    "hist": "history",
}

COORD_MIN = 0
COORD_MAX = 1000


class InputManager:
    """Parses commands and validates coordinates; keeps a history."""

    def __init__(self):
        self.command_history = []
        try:
            import readline  # noqa: F401  (enables arrow-key history)
            self._readline = readline
        except ImportError:
            self._readline = None

    def parse_command(self, line):
        """Return (command, args) with shortcuts expanded."""
        line = (line or "").strip()
        if not line:
            return "", []
        self.command_history.append(line)
        parts = line.replace(",", " ").replace("[", " ") \
            .replace("]", " ").split()
        cmd = parts[0].lower()
        return SHORTCUTS.get(cmd, cmd), parts[1:]

    @staticmethod
    def validate_coordinates(tokens):
        """Validate four integer coordinates; raise ValueError if invalid."""
        if isinstance(tokens, str):
            tokens = tokens.replace(",", " ").replace("[", " ") \
                .replace("]", " ").split()
        tokens = list(tokens)
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(str(t))
            except ValueError:
                raise ValueError("'%s' is not an integer" % t)
            if not COORD_MIN <= v <= COORD_MAX:
                raise ValueError("Coordinate %d out of range %d-%d"
                                 % (v, COORD_MIN, COORD_MAX))
            values.append(v)
        return values
