"""Command parsing and input validation."""

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "q": "quit", "exit": "quit", "h": "help", "?": "help",
    "t": "tick", "hist": "history",
}

COMMANDS = ("start", "status", "orders", "riders", "quit", "help",
            "tick", "run", "history", "save", "load", "map")

HELP_TEXT = """Commands:
  start [rx ry cx cy] (s)  create an order (coordinates 0-800)
  status (st)              system snapshot
  orders (o)               all order details
  riders (r)               rider status change history
  map                      show the map
  tick [n] (t)             advance n ticks (default 1)
  run                      advance until all orders delivered
  save [file] / load [file] persist / restore state (JSON)
  history (hist)           show command history
  help (h)                 this help
  quit / exit (q)          leave the program"""


class InputManager:
    """Parses commands and validates user input."""

    def __init__(self):
        self.history = []

    def parse(self, line):
        """Return (command, args) for an input line."""
        line = (line or "").strip()
        if not line:
            return "", []
        self.history.append(line)
        if len(self.history) > 500:
            self.history = self.history[-500:]
        parts = line.replace(",", " ").replace("[", " ").replace("]", " ").split()
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        return cmd, parts[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Parse 4 integer coordinates in range 0-800.

        Returns (coords, error_message); one of them is None.
        """
        if isinstance(tokens, str):
            tokens = tokens.replace(",", " ").replace("[", " ").replace(
                "]", " ").split()
        if len(tokens) != 4:
            return None, "Please enter exactly 4 integers: rx ry cx cy."
        coords = []
        for t in tokens:
            try:
                v = int(t)
            except (TypeError, ValueError):
                return None, "Invalid value '%s': coordinates must be integers." % t
            if not 0 <= v <= 800:
                return None, "Coordinate %d out of range (0-800)." % v
            coords.append(v)
        return coords, None

    @staticmethod
    def parse_positive_int(tokens, default=1):
        """Parse an optional positive integer argument."""
        if not tokens:
            return default, None
        try:
            v = int(tokens[0])
        except ValueError:
            return None, "Expected an integer."
        if v <= 0:
            return None, "Expected a positive integer."
        return v, None
