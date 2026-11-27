"""Input parsing and validation."""


class InputManager:
    """Parses commands and validates coordinates."""

    ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
               "q": "quit", "exit": "quit", "quit": "quit", "start": "start",
               "status": "status", "orders": "orders", "riders": "riders"}

    def __init__(self):
        self.history = []

    def parse_command(self, text):
        text = text.strip().lower()
        if text:
            self.history.append(text)
        return self.ALIASES.get(text)

    def parse_coordinates(self, text):
        """Return 4 ints or raise ValueError with clear message."""
        parts = text.replace(",", " ").replace("[", " ").replace("]", " ").split()
        if len(parts) != 4:
            raise ValueError("Please enter exactly four integers.")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers.")
        for v in vals:
            if not 0 <= v <= 1000:
                raise ValueError("Coordinates must be within 0-1000.")
        return vals
