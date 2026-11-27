"""Input parsing and validation."""

ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
           "q": "quit", "exit": "quit"}


class InputManager:
    """Parse commands."""

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        """Return (command, args)."""
        parts = line.strip().split()
        if not parts:
            return None, []
        self.history.append(line.strip())
        cmd = parts[0].lower()
        return ALIASES.get(cmd, cmd), parts[1:]

    @staticmethod
    def parse_coords(args):
        """Validate four integers in 0-800."""
        if len(args) != 4:
            raise ValueError("Need 4 integers: rx ry cx cy")
        try:
            v = [int(a) for a in args]
        except ValueError:
            raise ValueError("Coordinates must be integers")
        if any(n < 0 or n > 800 for n in v):
            raise ValueError("Coordinates must be within 0-800")
        return v
