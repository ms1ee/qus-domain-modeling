"""Command parsing and input validation."""

from config import INPUT_MAX, INPUT_MIN

ALIASES = {
    "start": "start", "s": "start", "order": "start", "new": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "run": "run",
    "save": "save", "load": "load",
    "history": "history", "hist": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "q": "quit", "exit": "quit",
}


class InputManager:
    """Parses commands, validates input and keeps command history."""

    def __init__(self, max_history=500):
        self.history = []
        self.max_history = max_history

    def record(self, line):
        """Add a line to the command history (bounded)."""
        if line.strip():
            self.history.append(line.strip())
            if len(self.history) > self.max_history:
                del self.history[0]

    def parse_command(self, line):
        """Return ``(command, args)``; command is None for empty input.

        ``!N`` repeats history entry N; ``!!`` repeats the last command.
        Unknown commands are returned as ``("unknown", [word])``.
        """
        line = (line or "").strip()
        if not line:
            return None, []
        if line == "!!" and self.history:
            line = self.history[-1]
        elif line.startswith("!") and line[1:].isdigit():
            idx = int(line[1:]) - 1
            if 0 <= idx < len(self.history):
                line = self.history[idx]
        parts = line.replace(",", " ").split()
        cmd = ALIASES.get(parts[0].lower())
        self.record(line)
        if cmd is None:
            return "unknown", [parts[0]]
        return cmd, parts[1:]

    @staticmethod
    def validate_coordinates(args):
        """Validate four integer coordinates in range 0-1000.

        Raises ValueError with a friendly message on failure.
        """
        if isinstance(args, str):
            args = args.replace(",", " ").replace("[", " ") \
                .replace("]", " ").split()
        args = [a for a in args if str(a).strip() not in ("[", "]")]
        cleaned = []
        for a in args:
            s = str(a).strip().strip("[]")
            if s:
                cleaned.append(s)
        if len(cleaned) != 4:
            raise ValueError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for s in cleaned:
            try:
                v = int(s)
            except ValueError:
                raise ValueError("'%s' is not an integer." % s)
            if not INPUT_MIN <= v <= INPUT_MAX:
                raise ValueError("Coordinate %d out of range (%d-%d)."
                                 % (v, INPUT_MIN, INPUT_MAX))
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(args, default=1):
        """Parse an optional positive integer argument."""
        if not args:
            return default
        try:
            v = int(args[0])
        except ValueError:
            raise ValueError("'%s' is not an integer." % args[0])
        if v < 1:
            raise ValueError("Value must be positive.")
        return v
