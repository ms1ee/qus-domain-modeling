"""Command parsing and input validation."""

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "q": "quit", "exit": "quit", "m": "map", "t": "tick", "h": "help",
    "?": "help", "hist": "history", "!!": "repeat",
}

COMMANDS = ("start", "status", "orders", "riders", "quit", "map", "tick",
            "run", "help", "history", "save", "repeat")

MIN_COORD = 0
MAX_COORD = 1000


class InputManager:
    """Parses commands, resolves shortcuts and keeps a command history."""

    def __init__(self):
        self.history = []

    def parse(self, line):
        """Return (command, args). Unknown commands are returned as-is."""
        tokens = (line or "").strip().split()
        if not tokens:
            return "", []
        cmd = tokens[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        return cmd, tokens[1:]

    def record(self, line):
        line = (line or "").strip()
        if line and not line.startswith("!!"):
            self.history.append(line)
            if len(self.history) > 500:
                del self.history[:-500]

    def last(self):
        return self.history[-1] if self.history else None

    @staticmethod
    def validate_coords(tokens):
        """Validate four integer coordinates.

        Returns (coords, error). ``coords`` is a list of 4 ints clamped to
        the 0-800 map, or None if invalid.
        """
        text = " ".join(tokens).replace(",", " ").replace("[", " ") \
            .replace("]", " ")
        parts = text.split()
        if len(parts) != 4:
            return None, "Please enter exactly 4 integers: rx ry cx cy"
        values = []
        for p in parts:
            try:
                v = int(p)
            except ValueError:
                return None, "Invalid integer: %r" % p
            if v < MIN_COORD or v > MAX_COORD:
                return None, "Coordinate %d out of range (%d-%d)" % (
                    v, MIN_COORD, MAX_COORD)
            values.append(min(v, 800))
        return values, None

    @staticmethod
    def help_text():
        return ("Commands:\n"
                "  start (s) [rx ry cx cy]  create an order\n"
                "  status (st)              system snapshot\n"
                "  orders (o)               all orders\n"
                "  riders (r)               rider event logs\n"
                "  map (m)                  ASCII map\n"
                "  tick (t) [n]             advance n ticks\n"
                "  run                      run until all orders complete\n"
                "  save                     save state to JSON\n"
                "  history (hist), !!       command history / repeat last\n"
                "  quit / exit (q)          exit")
