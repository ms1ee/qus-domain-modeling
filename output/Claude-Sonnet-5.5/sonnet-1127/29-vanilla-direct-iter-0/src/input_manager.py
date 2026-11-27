"""Input parsing and validation."""


class InputError(ValueError):
    """Invalid user input."""


def parse_coords(text):
    """Parse four integers in 0-800."""
    text = text.replace(",", " ").replace("[", " ").replace("]", " ")
    parts = text.split()
    if len(parts) != 4:
        raise InputError("Expected 4 integers: rx ry cx cy")
    try:
        vals = [int(p) for p in parts]
    except ValueError:
        raise InputError("Coordinates must be integers")
    for v in vals:
        if not 0 <= v <= 800:
            raise InputError("Coordinates must be within 0-800")
    return vals


class InputManager:
    """Command parsing with history and shortcuts."""

    SHORTCUTS = {"s": "start", "st": "status", "o": "orders",
                 "r": "riders", "q": "quit", "t": "tick"}

    def __init__(self):
        self.history = []

    def parse(self, line):
        """Return (command, argument string)."""
        line = line.strip()
        if not line:
            return "", ""
        self.history.append(line)
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        cmd = self.SHORTCUTS.get(cmd, cmd)
        return cmd, parts[1] if len(parts) > 1 else ""
