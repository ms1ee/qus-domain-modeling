"""Command parsing and input validation."""

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "q": "quit", "exit": "quit", "h": "help", "?": "help",
    "m": "map", "t": "tick", "hist": "history",
}

COMMANDS = ("start", "status", "orders", "riders", "quit", "help",
            "map", "tick", "history", "save", "load")

HELP_TEXT = """Commands:
  start (s) [rx ry cx cy]  create an order (coordinates 0-800)
  status (st)              funds, riders and map
  orders (o)               all order details
  riders (r)               rider status-change logs
  map (m)                  show map
  tick (t) [n]             advance simulation n ticks (default 1)
  history (hist)           show command history
  save <file> / load <file> persist state as JSON
  quit / exit (q)          exit"""


class InputManager:
    """Parses commands, keeps history and validates coordinates."""

    def __init__(self):
        self.command_history = []
        try:  # optional line editing / history support
            import readline  # noqa: F401
        except ImportError:
            pass

    def parse_command(self, line):
        """Return (command, args). Unknown commands are returned as-is."""
        line = (line or "").strip()
        if not line:
            return "", []
        self.command_history.append(line)
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        rest = parts[1] if len(parts) > 1 else ""
        return cmd, self.tokenize(rest)

    @staticmethod
    def tokenize(text):
        """Split text on spaces/commas, ignoring brackets."""
        for ch in "[](),":
            text = text.replace(ch, " ")
        return text.split()

    @staticmethod
    def validate_coordinates(tokens):
        """Validate four integer coordinates in 0..800.

        Raises:
            ValueError: with a user-friendly message.
        """
        if len(tokens) != 4:
            raise ValueError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for t in tokens:
            if isinstance(t, bool):
                raise ValueError("Invalid coordinate: %r" % (t,))
            if isinstance(t, int):
                v = t
            else:
                try:
                    v = int(str(t).strip())
                except ValueError:
                    raise ValueError("'%s' is not an integer" % t)
            if v < 0 or v > 800:
                raise ValueError("Coordinate %d out of range 0-800" % v)
            values.append(v)
        return values
