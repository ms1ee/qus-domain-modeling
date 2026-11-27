"""Input parsing and validation."""

try:
    import readline  # noqa: F401  (command history)
except ImportError:  # pragma: no cover
    readline = None

ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
           "q": "quit", "n": "tick"}


class InputManager:
    """Parses commands and validates coordinates."""

    def parse_command(self, line):
        parts = line.strip().split()
        if not parts:
            return None, []
        cmd = parts[0].lower()
        return ALIASES.get(cmd, cmd), parts[1:]

    def parse_coords(self, text):
        """Parse four integers in 0-1000; raises ValueError."""
        text = text.replace("[", " ").replace("]", " ").replace(",", " ")
        parts = text.split()
        if len(parts) != 4:
            raise ValueError("Need exactly four integers: rx ry cx cy")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers")
        for v in vals:
            if not 0 <= v <= 1000:
                raise ValueError("Coordinates must be within 0-1000")
        return vals
