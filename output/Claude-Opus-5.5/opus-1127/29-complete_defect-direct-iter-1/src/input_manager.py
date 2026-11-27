"""Command parsing and input validation."""

from path_planner import MAP_SIZE

ALIASES = {
    "start": "start", "s": "start", "new": "start", "n": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick", "wait": "tick",
    "history": "history", "hist": "history",
    "save": "save",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}


class InputManager:
    """Reads commands, keeps history, validates input."""

    def __init__(self, input_func=input):
        self.input_func = input_func
        self.history = []
        try:  # command history / line editing where available
            import readline  # noqa: F401
        except ImportError:
            pass

    def read_command(self, prompt="> "):
        """Read a line; supports '!!' to repeat the last command."""
        line = self.input_func(prompt).strip()
        if line == "!!":
            if not self.history:
                return ""
            line = self.history[-1]
            print(line)
        if line:
            self.history.append(line)
            if len(self.history) > 1000:
                del self.history[:-1000]
        return line

    @staticmethod
    def parse(line):
        """Parse a line into (command, args). Unknown commands -> (None, args)."""
        tokens = line.strip().split()
        if not tokens:
            return "", []
        cmd = ALIASES.get(tokens[0].lower())
        return cmd, tokens[1:]

    @staticmethod
    def tokenize_coordinates(text):
        """Split coordinate text, accepting brackets and commas."""
        for ch in "[](),":
            text = text.replace(ch, " ")
        return text.split()

    @staticmethod
    def validate_coordinates(tokens):
        """Validate 4 integer coordinates in range 0-800.

        Raises ValueError with a friendly message on failure.
        """
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y (got %d values)" % len(tokens))
        values = []
        for t in tokens:
            try:
                v = int(t)
            except (TypeError, ValueError):
                raise ValueError("'%s' is not an integer" % t)
            if v < 0 or v > MAP_SIZE:
                raise ValueError("Coordinate %d out of range 0-%d" % (v, MAP_SIZE))
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(tokens, default=1, maximum=10000):
        """Parse an optional positive integer argument."""
        if not tokens:
            return default
        try:
            v = int(tokens[0])
        except ValueError:
            raise ValueError("'%s' is not an integer" % tokens[0])
        if v < 1 or v > maximum:
            raise ValueError("Value must be between 1 and %d" % maximum)
        return v
