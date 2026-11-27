"""Input parsing and validation."""

ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
           "q": "quit", "exit": "quit", "h": "help", "?": "help"}


class InputManager:
    """Command parsing."""

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        line = line.strip().lower()
        if line:
            self.history.append(line)
        return ALIASES.get(line, line)

    @staticmethod
    def parse_coords(line):
        """Return 4 ints in 0..800, or raise ValueError."""
        parts = line.replace(",", " ").replace("[", " ").replace(
            "]", " ").split()
        if len(parts) != 4:
            raise ValueError("Enter exactly four integers.")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers.")
        if any(v < 0 or v > 800 for v in vals):
            raise ValueError("Coordinates must be within 0-800.")
        return vals
