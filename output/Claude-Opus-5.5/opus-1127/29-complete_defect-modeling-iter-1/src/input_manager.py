"""Command parsing and input validation."""

from grid_map import MAP_SIZE


class InputError(ValueError):
    """Raised for invalid user input."""


COMMAND_ALIASES = {
    "start": "start", "n": "start", "new": "start", "1": "start",
    "status": "status", "s": "status", "2": "status",
    "orders": "orders", "o": "orders", "3": "orders",
    "riders": "riders", "r": "riders", "4": "riders",
    "map": "map", "m": "map", "5": "map",
    "tick": "tick", "t": "tick", "6": "tick",
    "history": "history", "h": "history",
    "save": "save",
    "check": "check",
    "help": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}


class InputManager:
    """Parses commands, keeps command history, validates input."""

    def __init__(self, max_history=500):
        self.command_history = []
        self.max_history = max_history

    def read_line(self, prompt):
        """Read a line from stdin; EOF/interrupt becomes ``quit``."""
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"

    def record(self, raw):
        """Add a command to history."""
        self.command_history.append(raw)
        if len(self.command_history) > self.max_history:
            del self.command_history[:-self.max_history]

    def resolve_history(self, raw):
        """Expand ``!!`` and ``!n`` history references."""
        raw = raw.strip()
        if raw == "!!":
            if not self.command_history:
                raise InputError("No command history.")
            return self.command_history[-1]
        if raw.startswith("!"):
            try:
                n = int(raw[1:])
                return self.command_history[n - 1]
            except (ValueError, IndexError):
                raise InputError("Invalid history reference: %s" % raw)
        return raw

    def parse(self, raw):
        """Parse a raw line into ``(command, args)``.

        Unknown commands yield ``(None, args)``; empty lines ``("", [])``.
        """
        raw = self.resolve_history(raw)
        tokens = tokenize(raw)
        if not tokens:
            return "", []
        self.record(raw)
        return COMMAND_ALIASES.get(tokens[0].lower()), tokens[1:]

    @staticmethod
    def validate_coordinates(tokens):
        """Validate four integer coordinates in range 0..800."""
        if isinstance(tokens, str):
            tokens = tokenize(tokens)
        tokens = list(tokens)
        if len(tokens) != 4:
            raise InputError("Expected 4 coordinates: restaurant_x restaurant_y "
                             "customer_x customer_y (got %d)." % len(tokens))
        values = []
        for t in tokens:
            if isinstance(t, bool):
                raise InputError("Coordinate %r is not an integer." % (t,))
            if isinstance(t, int):
                v = t
            else:
                try:
                    v = int(str(t).strip())
                except ValueError:
                    raise InputError("Coordinate %r is not an integer." % (t,))
            if not 0 <= v <= MAP_SIZE:
                raise InputError("Coordinate %d out of range 0-%d." % (v, MAP_SIZE))
            values.append(v)
        return values


def tokenize(raw):
    """Split a line on whitespace/commas, stripping brackets."""
    for ch in "[](),":
        raw = raw.replace(ch, " ")
    return raw.split()
