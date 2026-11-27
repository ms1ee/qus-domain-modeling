"""Command parsing, shortcuts, history and input validation."""

try:  # optional line editing / arrow-key history
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows without readline
    readline = None

COMMANDS = ("start", "status", "orders", "riders", "map", "tick", "run",
            "save", "load", "history", "help", "quit")

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "m": "map", "t": "tick", "ru": "run", "hi": "history",
    "h": "help", "?": "help", "q": "quit", "exit": "quit",
}


class InputManager:
    """Reads and validates user commands."""

    def __init__(self, input_func=input):
        self.command_history = []
        self._input = input_func

    def read_line(self, prompt="> "):
        """Read a line; EOF/interrupt becomes ``quit``."""
        try:
            return self._input(prompt)
        except (EOFError, KeyboardInterrupt):
            return "quit"

    def parse(self, line):
        """Parse a line into (command, args).

        Supports shortcuts and ``!n`` / ``!!`` history recall.  Returns
        (None, []) for an empty line and ("unknown", [word]) for unknown
        commands.
        """
        line = (line or "").strip()
        if not line:
            return None, []
        if line.startswith("!"):
            ref = line[1:]
            if not self.command_history:
                return "error", ["history is empty"]
            if ref == "!":
                line = self.command_history[-1]
            else:
                try:
                    idx = int(ref)
                    line = self.command_history[idx - 1]
                except (ValueError, IndexError):
                    return "error", ["invalid history reference: %s" % line]
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        tokens = line.replace(",", " ").replace("[", " ").replace("]", " ").split()
        word = tokens[0].lower()
        cmd = SHORTCUTS.get(word, word)
        if cmd not in COMMANDS:
            return "unknown", [word]
        return cmd, tokens[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Validate four integer coordinates in range 0-800.

        Raises:
            ValueError with a user friendly message.
        """
        if isinstance(tokens, str):
            tokens = tokens.replace(",", " ").replace("[", " ").replace("]", " ").split()
        if len(tokens) != 4:
            raise ValueError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(t)
            except (TypeError, ValueError):
                raise ValueError("'%s' is not an integer" % t)
            if v < 0 or v > 800:
                raise ValueError("Coordinate %d out of range (0-800)" % v)
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(tokens, default=1, maximum=100000):
        """Parse an optional positive integer argument."""
        if not tokens:
            return default
        try:
            v = int(tokens[0])
        except ValueError:
            raise ValueError("'%s' is not an integer" % tokens[0])
        if v < 1 or v > maximum:
            raise ValueError("value must be between 1 and %d" % maximum)
        return v

    def history_text(self):
        """Numbered command history."""
        if not self.command_history:
            return "No history."
        return "\n".join("%3d  %s" % (i + 1, c)
                         for i, c in enumerate(self.command_history))

    @staticmethod
    def help_text():
        """Command overview."""
        return "\n".join([
            "Commands (shortcut):",
            "  start (s) [rx ry cx cy]  create an order (coordinates 0-800)",
            "  status (st)              funds and rider status",
            "  orders (o)               all order details",
            "  riders (r)               rider status change log",
            "  map (m)                  ASCII map",
            "  tick (t) [n]             advance simulation n ticks",
            "  run (ru)                 run until all orders delivered",
            "  save [file] / load [file] persist / restore state (JSON)",
            "  history (hi)             command history, !n or !! to repeat",
            "  help (h, ?)              this help",
            "  quit (q, exit)           leave the program",
        ])
