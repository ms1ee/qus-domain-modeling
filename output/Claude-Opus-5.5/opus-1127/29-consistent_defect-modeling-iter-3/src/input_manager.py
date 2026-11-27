"""Command parsing and input validation."""

SHORTCUTS = {
    "n": "start", "s": "status", "o": "orders", "r": "riders",
    "m": "map", "t": "tick", "q": "quit", "h": "help", "?": "help",
}

COMMANDS = ("start", "status", "orders", "riders", "map", "tick", "run",
            "save", "load", "history", "help", "quit", "exit")


class InputManager:
    """Parses commands, keeps history and validates coordinates."""

    def __init__(self, min_coord=0, max_coord=800):
        self.command_history = []
        self.min_coord = min_coord
        self.max_coord = max_coord

    def parse_command(self, line):
        """Return (command, args) or raise ValueError."""
        line = (line or "").strip()
        if not line:
            return "", []
        if line == "!!":
            if not self.command_history:
                raise ValueError("No command history.")
            line = self.command_history[-1]
        elif line.startswith("!") and line[1:].isdigit():
            idx = int(line[1:]) - 1
            if not 0 <= idx < len(self.command_history):
                raise ValueError("No such history entry.")
            line = self.command_history[idx]
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        if cmd not in COMMANDS:
            raise ValueError("Unknown command '%s'. Type 'help'." % parts[0])
        args = parts[1].split() if len(parts) > 1 else []
        return cmd, args

    def parse_coordinates(self, text):
        """Parse four integer coordinates; raise ValueError if invalid."""
        if isinstance(text, (list, tuple)):
            text = " ".join(str(t) for t in text)
        cleaned = text.replace("[", " ").replace("]", " ").replace(",", " ")
        tokens = cleaned.split()
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(t)
            except ValueError:
                raise ValueError("'%s' is not an integer." % t)
            if not self.min_coord <= v <= self.max_coord:
                raise ValueError("Coordinate %d out of range (%d-%d)." % (
                    v, self.min_coord, self.max_coord))
            values.append(v)
        return values
