"""Command parsing and input validation."""

COMMANDS = {
    "start": ("s", "1"),
    "status": ("st", "2"),
    "orders": ("o", "3"),
    "riders": ("r", "4"),
    "tick": ("t",),
    "map": ("m",),
    "history": ("hist",),
    "help": ("h", "?"),
    "quit": ("q", "exit"),
}


class Command:
    """A named command with shortcuts."""

    def __init__(self, name, shortcuts):
        self.name = name
        self.shortcuts = tuple(shortcuts)
        self.shortcut = self.shortcuts[0] if self.shortcuts else ""


class InputManager:
    """Parses commands, keeps history and validates coordinates."""

    def __init__(self, min_coordinate=0, max_coordinate=1000):
        self.command_history = []
        self.min_coordinate = min_coordinate
        self.max_coordinate = max_coordinate
        self.commands = {n: Command(n, s) for n, s in COMMANDS.items()}
        self._lookup = {}
        for name, cmd in self.commands.items():
            self._lookup[name] = name
            for s in cmd.shortcuts:
                self._lookup[s] = name

    def parse(self, line):
        """Return ``(command_name or None, args)`` for an input line.

        ``!N`` re-runs history entry N (1-based), ``!!`` the last one.
        """
        line = (line or "").strip()
        if not line:
            return None, []
        if line.startswith("!") and self.command_history:
            ref = line[1:]
            if ref == "!":
                line = self.command_history[-1]
            elif ref.isdigit() and 1 <= int(ref) <= len(self.command_history):
                line = self.command_history[int(ref) - 1]
            else:
                return None, []
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        tokens = line.split(None, 1)
        name = self._lookup.get(tokens[0].lower())
        rest = tokens[1] if len(tokens) > 1 else ""
        return name, self.tokenize(rest)

    @staticmethod
    def tokenize(text):
        """Split free text containing brackets/commas into tokens."""
        for ch in "[](),":
            text = text.replace(ch, " ")
        return text.split()

    def parse_coordinates(self, tokens):
        """Validate four integer coordinates and return them.

        Raises ValueError with a friendly message on failure.
        """
        if isinstance(tokens, str):
            tokens = self.tokenize(tokens)
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y (got %d values)" % len(tokens))
        values = []
        for t in tokens:
            try:
                v = int(t)
            except (TypeError, ValueError):
                raise ValueError("'%s' is not an integer" % t) from None
            if not self.min_coordinate <= v <= self.max_coordinate:
                raise ValueError("Coordinate %d out of range %d-%d" % (
                    v, self.min_coordinate, self.max_coordinate))
            values.append(v)
        return values

    def help_text(self):
        """Help listing."""
        lines = ["Commands (shortcuts in brackets):"]
        desc = {
            "start": "create an order: start rx ry cx cy",
            "status": "show funds and riders",
            "orders": "show all orders",
            "riders": "show rider status change history",
            "tick": "advance simulation: tick [n]",
            "map": "show the ASCII map",
            "history": "show command history (!N re-runs, !! last)",
            "help": "show this help",
            "quit": "save and exit",
        }
        for name, cmd in self.commands.items():
            lines.append("  %-8s [%s]  %s" % (name, ",".join(cmd.shortcuts),
                                              desc[name]))
        lines.append("Each command advances the simulation by one tick.")
        return "\n".join(lines)
