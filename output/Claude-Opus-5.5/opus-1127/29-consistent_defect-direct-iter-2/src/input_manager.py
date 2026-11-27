"""Command parsing and input validation."""

SHORTCUTS = {"s": "start", "st": "status", "o": "orders", "r": "riders",
             "q": "quit", "exit": "quit", "h": "help"}
COMMANDS = {"start", "status", "orders", "riders", "quit", "help", "history"}


class InputManager:
    """Parses commands and validates coordinates."""

    def __init__(self):
        self.history = []
        try:
            import readline  # noqa: F401  (enables arrow-key history)
        except ImportError:
            pass

    def parse_command(self, text):
        cmd = text.strip().lower()
        if cmd:
            self.history.append(cmd)
        cmd = SHORTCUTS.get(cmd, cmd)
        return cmd if cmd in COMMANDS else None

    @staticmethod
    def parse_coords(text):
        """Parse four integers in range 0-800. Raises ValueError on error."""
        parts = text.replace(",", " ").replace("[", " ").replace("]", " ").split()
        if len(parts) != 4:
            raise ValueError("Expected exactly 4 integers.")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers.")
        for v in vals:
            if v < 0 or v > 800:
                raise ValueError("Coordinates must be in range 0-800.")
        return vals
