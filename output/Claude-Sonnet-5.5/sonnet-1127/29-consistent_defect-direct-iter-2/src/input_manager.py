"""Input parsing and validation."""


class InputManager:
    """Parse commands."""

    @staticmethod
    def parse_coords(text):
        """Parse four integers in 0-1000; raise ValueError otherwise."""
        parts = text.replace(",", " ").replace("[", " ").replace("]", " ").split()
        if len(parts) != 4:
            raise ValueError("Enter exactly four integers.")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers.")
        for v in vals:
            if not 0 <= v <= 1000:
                raise ValueError("Coordinates must be within 0-1000.")
        return vals
