"""Command parsing and validation."""

ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
           "q": "quit", "exit": "quit", "quit": "quit", "start": "start",
           "status": "status", "orders": "orders", "riders": "riders",
           "h": "history", "history": "history"}


class InputManager:
    """Parses commands and validates coordinates."""

    def __init__(self):
        self.command_history = []

    def parse_command(self, line):
        """Return (command, args) or (None, []) if blank/unknown."""
        parts = line.strip().split()
        if not parts:
            return None, []
        self.command_history.append(line.strip())
        return ALIASES.get(parts[0].lower(), "unknown"), parts[1:]

    @staticmethod
    def parse_coords(tokens):
        """Validate four integers in 0-800; raises ValueError."""
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: rx ry cx cy")
        try:
            vals = [int(t) for t in tokens]
        except ValueError:
            raise ValueError("Coordinates must be integers")
        for v in vals:
            if v < 0 or v > 800:
                raise ValueError("Coordinates must be within 0-800")
        return vals
