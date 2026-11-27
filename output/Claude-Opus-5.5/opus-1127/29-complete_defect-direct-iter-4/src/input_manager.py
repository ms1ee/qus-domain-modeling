"""Command parsing and input validation."""

try:  # command history support where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

ALIASES = {
    "s": "start", "start": "start",
    "st": "status", "status": "status",
    "o": "orders", "orders": "orders",
    "r": "riders", "riders": "riders",
    "m": "map", "map": "map",
    "t": "tick", "tick": "tick",
    "run": "run",
    "save": "save", "load": "load",
    "hist": "history", "history": "history",
    "h": "help", "help": "help", "?": "help",
    "q": "quit", "quit": "quit", "exit": "quit",
}

HELP_TEXT = """Commands:
  start (s) [rx ry cx cy]  create an order (coordinates 0-800)
  status (st)              system snapshot
  orders (o)               list all orders
  riders (r)               rider status-change records
  map (m)                  show the ASCII map
  tick (t) [n]             advance simulation n ticks
  run                      run until all orders are delivered
  save [file] / load [file] persist / restore state (JSON)
  history (hist)           show command history
  help (h)                 show this help
  quit / exit (q)          exit"""


class InputManager:
    """Parses commands and validates user input."""

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        """Return (command, args). Unknown commands return (None, args)."""
        line = (line or "").strip()
        if not line:
            return "", []
        self.history.append(line)
        parts = line.split()
        cmd = ALIASES.get(parts[0].lower())
        return cmd, parts[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Parse four integer coordinates in 0-800; raise ValueError."""
        if isinstance(tokens, str):
            tokens = tokens.replace(",", " ").replace("[", " ") \
                .replace("]", " ").split()
        else:
            joined = " ".join(str(t) for t in tokens)
            tokens = joined.replace(",", " ").replace("[", " ") \
                .replace("]", " ").split()
        if len(tokens) != 4:
            raise ValueError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(t)
            except ValueError:
                raise ValueError("'%s' is not an integer." % t)
            if v < 0 or v > 800:
                raise ValueError("Coordinate %d out of range (0-800)." % v)
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(token, default=1):
        """Parse a positive integer argument."""
        if token is None:
            return default
        v = int(token)
        if v <= 0:
            raise ValueError("Value must be positive.")
        return v
