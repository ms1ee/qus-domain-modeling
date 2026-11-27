"""Command parsing and input validation."""

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows
    readline = None

MIN_COORD = 0
MAX_COORD = 800


class InputError(ValueError):
    """Raised for invalid user input."""


class InputManager:
    """Parses commands, supports shortcuts and keeps command history."""

    SHORTCUTS = {
        "n": "start", "new": "start", "s": "status", "o": "orders",
        "r": "riders", "m": "map", "t": "tick", "h": "history",
        "q": "quit", "exit": "quit", "?": "help",
    }
    COMMANDS = ("start", "status", "orders", "riders", "map", "tick",
                "history", "save", "load", "help", "quit")

    def __init__(self, max_history=500):
        self.command_history = []
        self.max_history = max_history

    def add_history(self, line):
        self.command_history.append(line)
        if len(self.command_history) > self.max_history:
            del self.command_history[:len(self.command_history) - self.max_history]

    def _resolve_history(self, line):
        if not self.command_history:
            raise InputError("command history is empty")
        if line == "!!":
            return self.command_history[-1]
        try:
            idx = int(line[1:])
        except ValueError:
            raise InputError("use !! or !<number> to repeat a command")
        if idx < 1 or idx > len(self.command_history):
            raise InputError("no history entry %d" % idx)
        return self.command_history[idx - 1]

    def parse(self, line):
        """Return (command, args)."""
        line = (line or "").strip()
        if not line:
            return "", []
        if line.startswith("!"):
            line = self._resolve_history(line)
            print("> " + line)
        self.add_history(line)
        tokens = line.replace(",", " ").replace("[", " ").replace("]", " ").split()
        if not tokens:
            return "", []
        cmd = tokens[0].lower()
        cmd = self.SHORTCUTS.get(cmd, cmd)
        return cmd, tokens[1:]

    @staticmethod
    def validate_coordinates(tokens):
        """Validate four integer coordinates in range 0-800."""
        if isinstance(tokens, str):
            tokens = tokens.replace(",", " ").replace("[", " ").replace("]", " ").split()
        tokens = list(tokens)
        if len(tokens) != 4:
            raise InputError("expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y (got %d)" % len(tokens))
        values = []
        for tok in tokens:
            try:
                value = int(str(tok).strip())
            except ValueError:
                raise InputError("'%s' is not an integer" % tok)
            if not MIN_COORD <= value <= MAX_COORD:
                raise InputError("coordinate %d out of range %d-%d"
                                 % (value, MIN_COORD, MAX_COORD))
            values.append(value)
        return values

    def prompt_coordinates(self, reader=input):
        """Ask the user for the four coordinates."""
        line = reader("Enter restaurant_x restaurant_y customer_x customer_y "
                      "(0-800): ")
        return self.validate_coordinates(line)

    @staticmethod
    def help_text():
        return "\n".join([
            "Commands (shortcut in brackets):",
            "  start [rx ry cx cy] (n)  create an order (coordinates 0-800)",
            "  status (s)               funds and rider states",
            "  orders (o)               all order details",
            "  riders (r)               rider status change log",
            "  map (m)                  ASCII map",
            "  tick [n] (t)             advance simulated time n ticks",
            "  history (h)              command history; !! or !<n> repeats",
            "  save [file] / load [file] persist / restore state (JSON)",
            "  help (?)                 this help",
            "  quit / exit (q)          leave the program",
            "Each processed command advances the simulation by one tick.",
        ])
