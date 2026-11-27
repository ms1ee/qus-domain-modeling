"""Command parsing and input validation."""

from path_planner import MAP_SIZE

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

SHORTCUTS = {
    "s": "start", "start": "start",
    "st": "status", "status": "status",
    "o": "orders", "orders": "orders",
    "r": "riders", "riders": "riders",
    "m": "map", "map": "map",
    "t": "tick", "tick": "tick",
    "hi": "history", "history": "history",
    "save": "save",
    "h": "help", "help": "help", "?": "help",
    "q": "quit", "quit": "quit", "exit": "quit",
}


class InputManager:
    """Parses commands and validates user input."""

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        """Return (command, args). Unknown commands yield ('unknown', ...)."""
        line = (line or "").strip()
        if not line:
            return "", []
        self.history.append(line)
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        tokens = line.replace(",", " ").replace("[", " ") \
            .replace("]", " ").split()
        cmd = SHORTCUTS.get(tokens[0].lower(), "unknown")
        return cmd, tokens[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Validate four integer coordinates in 0..800.

        Raises ValueError with a friendly message on bad input.
        """
        if isinstance(tokens, str):
            tokens = tokens.replace(",", " ").replace("[", " ") \
                .replace("]", " ").split()
        if len(tokens) != 4:
            raise ValueError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(t)
            except (TypeError, ValueError):
                raise ValueError("'%s' is not an integer" % t)
            if v < 0 or v > MAP_SIZE:
                raise ValueError("coordinate %d out of range 0-%d"
                                 % (v, MAP_SIZE))
            values.append(v)
        return values

    @staticmethod
    def parse_tick_count(tokens):
        if not tokens:
            return 1
        try:
            n = int(tokens[0])
        except ValueError:
            raise ValueError("tick count must be an integer")
        if n < 1 or n > 10000:
            raise ValueError("tick count must be between 1 and 10000")
        return n
