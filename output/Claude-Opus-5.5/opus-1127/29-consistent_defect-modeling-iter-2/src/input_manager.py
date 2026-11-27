"""Command parsing, input validation and command history."""

import re

try:  # Optional line editing / history shortcuts (not on all platforms).
    import readline  # noqa: F401
except Exception:  # pragma: no cover
    readline = None

ALIASES = {
    "s": "start", "n": "start", "new": "start",
    "st": "status", "o": "orders", "r": "riders",
    "q": "quit", "exit": "quit", "h": "help", "?": "help",
    "t": "tick", "m": "map", "hist": "history",
}

COMMANDS = {"start", "status", "orders", "riders", "quit", "help", "tick",
            "run", "map", "history", "save", "load"}


class InputManager:
    """Parses commands and validates coordinate input."""

    def __init__(self, min_coord=0, max_coord=1000):
        self.min_coord = min_coord
        self.max_coord = max_coord
        self.command_history = []

    def read(self, prompt="> "):
        """Read a line from the user, supporting '!!' to repeat."""
        line = input(prompt).strip()
        if line == "!!":
            if not self.command_history:
                raise ValueError("no command history")
            line = self.command_history[-1]
            print(line)
        if line:
            self.command_history.append(line)
        return line

    @staticmethod
    def parse_command(line):
        """Split a line into (command, args) and resolve aliases."""
        parts = line.strip().split(None, 1)
        if not parts:
            return "", ""
        cmd = parts[0].lower()
        cmd = ALIASES.get(cmd, cmd)
        args = parts[1] if len(parts) > 1 else ""
        return cmd, args

    def parse_coordinates(self, text):
        """Parse four integer coordinates; raise ValueError on bad input."""
        if isinstance(text, (list, tuple)):
            tokens = [str(t) for t in text]
        else:
            tokens = [t for t in re.split(r"[\s,\[\]()]+", str(text)) if t]
        if len(tokens) != 4:
            raise ValueError("please enter exactly four integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(t)
            except ValueError:
                raise ValueError(f"'{t}' is not an integer") from None
            if not self.min_coord <= v <= self.max_coord:
                raise ValueError(f"coordinate {v} out of range "
                                 f"[{self.min_coord}, {self.max_coord}]")
            values.append(v)
        return values

    @staticmethod
    def parse_positive_int(text, default=1):
        text = (text or "").strip()
        if not text:
            return default
        v = int(text)
        if v <= 0:
            raise ValueError("value must be positive")
        return v
