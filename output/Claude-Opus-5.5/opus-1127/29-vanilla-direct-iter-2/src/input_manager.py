"""Command parsing, shortcuts, history and input validation."""

SHORTCUTS = {
    "s": "start", "start": "start",
    "st": "status", "status": "status",
    "o": "orders", "orders": "orders",
    "r": "riders", "riders": "riders",
    "m": "map", "map": "map",
    "t": "tick", "tick": "tick",
    "run": "run",
    "save": "save",
    "hist": "history", "history": "history",
    "h": "help", "?": "help", "help": "help",
    "q": "quit", "quit": "quit", "exit": "quit",
}

HELP_TEXT = """Commands (shortcut in brackets):
  start [s] [rx ry cx cy]  Create an order (coordinates 0-800)
  status [st]              Funds and rider states
  orders [o]               Details of all orders
  riders [r]               Rider event history
  map [m]                  Show the ASCII map
  tick [t] [n]             Advance simulation n ticks (default 1)
  run                      Run until all orders are delivered
  save [file]              Save state to JSON
  history [hist]           Show command history ('!!' repeats last)
  help [h, ?]              Show this help
  quit/exit [q]            Exit the program
Each command loop iteration also advances time by one tick."""


class InputManager:
    """Parses commands and validates input."""

    def __init__(self):
        self.history = []
        try:
            import readline  # noqa: F401  (enables arrow-key history)
            self.readline = True
        except ImportError:
            self.readline = False

    def parse(self, line):
        """Parse a raw line into (command, args). Unknown -> ("unknown", [word])."""
        line = (line or "").strip()
        if line == "!!":
            if not self.history:
                return "empty", []
            line = self.history[-1]
        if not line:
            return "empty", []
        self.history.append(line)
        if len(self.history) > 500:
            del self.history[:-500]
        parts = line.replace(",", " ").replace("[", " ").replace("]", " ").split()
        cmd = SHORTCUTS.get(parts[0].lower())
        if cmd is None:
            return "unknown", parts[:1]
        return cmd, parts[1:]

    @staticmethod
    def validate_coordinates(tokens):
        """Validate four integer coordinates in range 0-800.

        Raises ValueError with a friendly message on failure.
        """
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y (got %d values)." % len(tokens))
        values = []
        for t in tokens:
            try:
                v = int(t)
            except (TypeError, ValueError):
                raise ValueError("'%s' is not an integer." % t)
            if v < 0 or v > 800:
                raise ValueError("Coordinate %d is out of range (0-800)." % v)
            values.append(v)
        return values

    def prompt_coordinates(self, input_func=input):
        """Prompt for coordinates until valid; returns list or None on cancel."""
        while True:
            raw = input_func("Enter restaurant_x restaurant_y customer_x customer_y "
                             "(blank to cancel): ").strip()
            if not raw:
                return None
            tokens = raw.replace(",", " ").replace("[", " ").replace("]", " ").split()
            try:
                return self.validate_coordinates(tokens)
            except ValueError as exc:
                print("Invalid input: %s" % exc)

    @staticmethod
    def parse_positive_int(tokens, default=1, maximum=100000):
        """Parse an optional positive integer argument."""
        if not tokens:
            return default
        v = int(tokens[0])
        if v <= 0:
            raise ValueError("Value must be positive.")
        return min(v, maximum)
