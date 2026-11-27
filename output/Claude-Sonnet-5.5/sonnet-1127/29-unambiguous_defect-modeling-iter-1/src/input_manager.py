"""Input parsing and validation."""

ALIASES = {"s": "status", "o": "orders", "r": "riders", "q": "quit",
           "exit": "quit", "h": "help", "st": "start"}


class InputManager:
    """Parses commands and keeps history."""

    def __init__(self):
        self.command_history = []

    def parse(self, line):
        """Return (command, args)."""
        parts = line.strip().split()
        if not parts:
            return None, []
        self.command_history.append(line.strip())
        cmd = parts[0].lower()
        return ALIASES.get(cmd, cmd), parts[1:]

    @staticmethod
    def parse_coords(args):
        """Validate four integers in 0-800."""
        if len(args) != 4:
            raise ValueError("Need 4 integers: rx ry cx cy")
        try:
            vals = [int(a) for a in args]
        except ValueError:
            raise ValueError("Coordinates must be integers")
        if any(v < 0 or v > 800 for v in vals):
            raise ValueError("Coordinates must be within 0-800")
        return vals
