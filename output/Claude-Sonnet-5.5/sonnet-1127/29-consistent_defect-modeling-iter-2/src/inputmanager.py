"""Input parsing and validation."""


class InputManager:
    """Parses commands."""

    COMMANDS = {"start": "start", "s": "start", "status": "status",
                "orders": "orders", "o": "orders", "riders": "riders",
                "r": "riders", "quit": "quit", "exit": "quit", "q": "quit"}

    def __init__(self):
        self.history = []

    def parse_command(self, text):
        text = text.strip().lower()
        if text:
            self.history.append(text)
        return self.COMMANDS.get(text)

    @staticmethod
    def parse_coordinates(text):
        """Parse four integers in 0..1000; raises ValueError."""
        parts = text.replace(",", " ").replace("[", " ").replace(
            "]", " ").split()
        if len(parts) != 4:
            raise ValueError("Expected 4 integers")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers")
        if any(v < 0 or v > 1000 for v in vals):
            raise ValueError("Coordinates must be within 0-1000")
        return vals
