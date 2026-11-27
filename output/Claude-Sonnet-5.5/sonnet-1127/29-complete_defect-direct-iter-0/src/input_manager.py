"""Input parsing and validation."""


class InputManager:
    """Parses commands."""

    ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
               "q": "quit", "exit": "quit", "t": "tick"}

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        parts = line.strip().split()
        if not parts:
            return None, []
        self.history.append(line.strip())
        cmd = parts[0].lower()
        return self.ALIASES.get(cmd, cmd), parts[1:]

    @staticmethod
    def parse_coords(tokens):
        """Validate four integers in 0-800."""
        if len(tokens) != 4:
            raise ValueError("Need exactly 4 integers: rx ry cx cy")
        try:
            vals = [int(t) for t in tokens]
        except ValueError:
            raise ValueError("Coordinates must be integers")
        for v in vals:
            if not 0 <= v <= 800:
                raise ValueError("Coordinates must be within 0-800")
        return vals
