"""Command parsing, shortcuts, history and input validation."""

try:  # optional line editing / arrow-key history
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

SHORTCUTS = {
    "s": "start", "new": "start", "start": "start",
    "st": "status", "status": "status",
    "o": "orders", "orders": "orders",
    "r": "riders", "riders": "riders",
    "m": "map", "map": "map",
    "t": "tick", "tick": "tick",
    "run": "run",
    "save": "save", "load": "load",
    "h": "help", "?": "help", "help": "help",
    "hist": "history", "history": "history",
    "q": "quit", "quit": "quit", "exit": "quit",
}

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] (s)  create an order; prompts if coordinates omitted
  status (st)              funds and rider states
  orders (o)               details of every order
  riders (r)               every status change of every rider
  map (m)                  ASCII map of riders and open orders
  tick [n] (t)             advance the simulation n ticks (default 1)
  run                      run until all orders are delivered
  save [file] / load [file] persist state as JSON
  history (hist)           show command history; !n repeats entry n, !! last
  help (h, ?)              this help
  quit / exit (q)          exit the program
Every command also advances the simulation by the configured ticks."""


class InputError(ValueError):
    """Raised for invalid user input."""


class InputManager:
    """Parses commands and validates coordinates."""

    def __init__(self, min_coord=0, max_coord=800):
        self.min_coord = min_coord
        self.max_coord = max_coord
        self.history = []

    def expand_history(self, line):
        """Expand ``!!`` and ``!n`` references to earlier commands."""
        line = line.strip()
        if line == "!!":
            if not self.history:
                raise InputError("No command history yet.")
            return self.history[-1]
        if line.startswith("!") and line[1:].isdigit():
            n = int(line[1:])
            if not 1 <= n <= len(self.history):
                raise InputError("No history entry %d." % n)
            return self.history[n - 1]
        return line

    def parse(self, line):
        """Return (command, args).  Unknown commands keep their raw name."""
        line = self.expand_history(line)
        tokens = line.replace(",", " ").replace("[", " ").replace("]", " ").split()
        if not tokens:
            return "", []
        self.history.append(line)
        if len(self.history) > 1000:
            del self.history[:-1000]
        cmd = tokens[0].lower()
        return SHORTCUTS.get(cmd, cmd), tokens[1:]

    def validate_coordinates(self, tokens):
        """Validate four integer coordinates in range; return list[int]."""
        if isinstance(tokens, str):
            tokens = tokens.replace(",", " ").replace("[", " ").replace("]", " ").split()
        tokens = list(tokens)
        if len(tokens) != 4:
            raise InputError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y (got %d)." % len(tokens))
        values = []
        for tok in tokens:
            try:
                v = int(str(tok).strip())
            except ValueError:
                raise InputError("'%s' is not an integer." % tok) from None
            if not self.min_coord <= v <= self.max_coord:
                raise InputError("Coordinate %d out of range %d-%d."
                                 % (v, self.min_coord, self.max_coord))
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(tokens, default=1):
        """Parse an optional positive integer argument."""
        if not tokens:
            return default
        try:
            v = int(tokens[0])
        except ValueError:
            raise InputError("'%s' is not an integer." % tokens[0]) from None
        if v <= 0:
            raise InputError("Value must be positive.")
        return v

    def format_history(self):
        """Numbered command history."""
        if not self.history:
            return "No history."
        return "\n".join("%4d  %s" % (i + 1, c) for i, c in enumerate(self.history))
