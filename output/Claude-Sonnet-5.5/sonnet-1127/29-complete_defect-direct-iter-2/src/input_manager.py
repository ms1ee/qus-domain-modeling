"""Input parsing and validation."""

ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
           "q": "quit", "exit": "quit", "t": "tick"}


class InputManager:
    """Parse commands and coordinates."""

    def __init__(self):
        self.history = []

    def parse_command(self, text):
        text = text.strip().lower()
        if text:
            self.history.append(text)
        return ALIASES.get(text, text)

    @staticmethod
    def parse_coords(text):
        """Parse four integers in 0-800; raise ValueError otherwise."""
        parts = text.replace(",", " ").replace("[", " ").replace("]", " ").split()
        if len(parts) != 4:
            raise ValueError("Expected four integers.")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers.")
        for v in vals:
            if not 0 <= v <= 800:
                raise ValueError("Coordinates must be within 0-800.")
        return vals
