"""Command parsing and validation."""


class InputManager:
    """Parses user input."""

    COMMANDS = {"start": "start", "s": "start", "status": "status",
                "orders": "orders", "o": "orders", "riders": "riders",
                "r": "riders", "map": "map", "m": "map", "tick": "tick",
                "t": "tick", "run": "run", "quit": "quit", "exit": "quit",
                "q": "quit", "help": "help", "h": "help"}

    def parse_command(self, line):
        parts = line.strip().split()
        if not parts:
            return None, []
        cmd = self.COMMANDS.get(parts[0].lower())
        return cmd, parts[1:]

    def parse_coords(self, text):
        """Parse four integers in 0-1000; raises ValueError."""
        text = text.replace("[", " ").replace("]", " ").replace(",", " ")
        parts = text.split()
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
