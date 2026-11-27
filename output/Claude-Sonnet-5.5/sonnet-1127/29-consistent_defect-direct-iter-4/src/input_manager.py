"""Command parsing and validation."""


class InputManager:
    """Parses user input."""

    def __init__(self):
        self.history = []

    def parse(self, line):
        """Return (command, args) or raise ValueError."""
        line = line.strip()
        if not line:
            raise ValueError("empty command")
        self.history.append(line)
        parts = line.split()
        cmd = parts[0].lower()
        aliases = {"s": "status", "o": "orders", "r": "riders",
                   "q": "quit", "exit": "quit"}
        return aliases.get(cmd, cmd), parts[1:]

    @staticmethod
    def parse_coords(text):
        """Parse four integers within 0-1000."""
        parts = text.replace(",", " ").replace("[", " ").replace(
            "]", " ").split()
        if len(parts) != 4:
            raise ValueError("need exactly 4 integers")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("coordinates must be integers")
        if any(v < 0 or v > 1000 for v in vals):
            raise ValueError("coordinates must be within 0-1000")
        return vals
