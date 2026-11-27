"""Command parsing and validation."""


class InputManager:
    """Parses user input."""

    ALIASES = {"s": "status", "o": "orders", "r": "riders", "q": "quit",
               "exit": "quit", "t": "tick", "h": "help"}

    def __init__(self):
        self.history = []

    def parse_command(self, line):
        cmd = line.strip().lower()
        if cmd:
            self.history.append(cmd)
        parts = cmd.split()
        if not parts:
            return "", []
        return self.ALIASES.get(parts[0], parts[0]), parts[1:]

    @staticmethod
    def parse_coords(line):
        """Parse four ints in 0-800. Raises ValueError with message."""
        text = line.replace(",", " ").replace("[", " ").replace("]", " ")
        parts = text.split()
        if len(parts) != 4:
            raise ValueError("Enter exactly four integers.")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers.")
        if any(v < 0 or v > 800 for v in vals):
            raise ValueError("Coordinates must be within 0-800.")
        return vals
