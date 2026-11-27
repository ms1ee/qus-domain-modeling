"""Command parsing and input validation."""

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "q": "quit", "exit": "quit", "h": "help", "?": "help",
    "m": "map", "t": "tick", "hist": "history", "sv": "save",
}
COMMANDS = {"start", "status", "orders", "riders", "quit", "help", "map",
            "tick", "history", "save"}


class InputManager:
    """Parses commands, validates coordinates and keeps history."""

    def __init__(self):
        self.history = []
        try:
            import readline  # noqa: F401  (enables arrow-key history)
            self._readline = readline
        except ImportError:
            self._readline = None

    def parse_command(self, line):
        """Return (command, args) or (None, []) for empty input."""
        parts = line.strip().split()
        if not parts:
            return None, []
        self.history.append(line.strip())
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        return cmd, parts[1:]

    @staticmethod
    def validate_coordinates(tokens):
        """Validate four integer coordinates in 0-800.

        Returns (True, [ints]) or (False, error_message).
        """
        tokens = [t for tok in tokens for t in tok.replace(",", " ").split()]
        if len(tokens) != 4:
            return False, ("Please enter exactly 4 integers: "
                           "restaurant_x restaurant_y customer_x customer_y")
        vals = []
        for t in tokens:
            try:
                v = int(t)
            except ValueError:
                return False, "'%s' is not an integer." % t
            if v < 0 or v > 800:
                return False, "Coordinate %d is out of range (0-800)." % v
            vals.append(v)
        return True, vals

    @staticmethod
    def validate_positive_int(token, default=1):
        """Parse a positive int, returning default on failure."""
        try:
            v = int(token)
            return v if v > 0 else default
        except (TypeError, ValueError):
            return default
