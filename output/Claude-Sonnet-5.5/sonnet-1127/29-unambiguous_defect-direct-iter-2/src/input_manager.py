"""Command parsing."""


class InputManager:
    """Parse and validate user input."""

    @staticmethod
    def parse_coords(text):
        """Parse four integers in 0-800. Raises ValueError."""
        cleaned = text.replace("[", " ").replace("]", " ").replace(",", " ")
        parts = cleaned.split()
        if len(parts) != 4:
            raise ValueError("Need exactly four integers.")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers.")
        if any(v < 0 or v > 800 for v in vals):
            raise ValueError("Coordinates must be within 0-800.")
        return vals

    ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
               "q": "quit", "exit": "quit", "t": "tick"}

    @classmethod
    def command(cls, line):
        """Normalise command word."""
        w = line.strip().lower()
        return cls.ALIASES.get(w, w)
