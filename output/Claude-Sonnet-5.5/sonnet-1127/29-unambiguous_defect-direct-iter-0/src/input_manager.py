"""Input parsing and validation."""


class InputManager:
    """Parses commands and validates coordinates."""

    ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
               "q": "quit", "exit": "quit"}

    @staticmethod
    def parse_command(text):
        t = text.strip().lower()
        return InputManager.ALIASES.get(t, t)

    @staticmethod
    def parse_coords(text):
        """Parse four integers in 0-800; raise ValueError otherwise."""
        parts = text.replace("[", " ").replace("]", " ").replace(",", " ").split()
        if len(parts) != 4:
            raise ValueError("Please enter exactly four integers.")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers.")
        if any(v < 0 or v > 800 for v in vals):
            raise ValueError("Coordinates must be within 0-800.")
        return vals
