"""Command parsing, shortcuts, history and input validation."""

from grid_map import MAP_SIZE

SHORTCUTS = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "q": "quit",
    "exit": "quit",
}

COMMANDS = ("start", "status", "orders", "riders", "map", "tick", "run",
            "history", "save", "help", "quit")


class InputManager:
    """Parses commands and validates user input."""

    def __init__(self):
        self.command_history = []
        try:  # optional line editing / arrow-key history
            import readline  # noqa: F401
        except ImportError:
            pass

    def resolve_history(self, line):
        """Expand '!n' (n-th command) and '!!' (last command)."""
        line = line.strip()
        if line == "!!":
            if not self.command_history:
                raise ValueError("No command history")
            return self.command_history[-1]
        if line.startswith("!") and len(line) > 1:
            try:
                n = int(line[1:])
            except ValueError:
                raise ValueError("Invalid history reference: %s" % line)
            if n < 1 or n > len(self.command_history):
                raise ValueError("History index out of range")
            return self.command_history[n - 1]
        return line

    def parse(self, line):
        """Return (command, args).  Unknown commands raise ValueError."""
        line = self.resolve_history(line or "")
        if not line:
            return "", []
        parts = line.split()
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        if cmd not in COMMANDS:
            raise ValueError("Unknown command '%s'. Type 'help'." % parts[0])
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        return cmd, parts[1:]

    @staticmethod
    def validate_coordinates(tokens):
        """Validate four integer coordinates in range 0-800."""
        if len(tokens) == 1:
            tokens = tokens[0].replace(",", " ").replace("[", " ") \
                .replace("]", " ").split()
        else:
            tokens = " ".join(tokens).replace(",", " ").replace("[", " ") \
                .replace("]", " ").split()
        if len(tokens) != 4:
            raise ValueError("Please enter exactly four integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(t)
            except ValueError:
                raise ValueError("'%s' is not an integer" % t)
            if v < 0 or v > MAP_SIZE:
                raise ValueError("Coordinate %d out of range 0-%d" % (v, MAP_SIZE))
            values.append(v)
        return values

    @staticmethod
    def validate_positive_int(tokens, default=1):
        """Parse an optional positive integer argument."""
        if not tokens:
            return default
        try:
            v = int(tokens[0])
        except ValueError:
            raise ValueError("'%s' is not an integer" % tokens[0])
        if v < 1:
            raise ValueError("Value must be positive")
        return v

    @staticmethod
    def help_text():
        """Help message."""
        return "\n".join([
            "Commands (shortcut):",
            "  start (s) [rx ry cx cy]  create order and dispatch it",
            "  status (st)              funds and rider states",
            "  orders (o)               all orders",
            "  riders (r)               rider status change logs",
            "  map (m)                  map with riders and active orders",
            "  tick (t) [n]             advance simulation n ticks",
            "  run                      advance until all orders complete",
            "  history                  show command history (!n / !! to repeat)",
            "  save                     save state to JSON",
            "  help (h, ?)              this help",
            "  quit / exit (q)          leave the program",
            "Each command also advances the simulation by one tick.",
        ])
