"""Command parsing and input validation."""

import config

try:  # command line editing/history where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows
    readline = None


class InputManager:
    """Parses commands, supports shortcuts and history, validates input."""

    SHORTCUTS = {
        "s": "start", "st": "status", "o": "orders", "r": "riders",
        "m": "map", "t": "tick", "h": "help", "?": "help",
        "q": "quit", "e": "exit", "hist": "history",
    }
    COMMANDS = {
        "start": "Input an order: start [rx ry cx cy] (0-800)",
        "status": "Show funds and rider states",
        "orders": "Show details of all orders",
        "riders": "Show rider status change log",
        "map": "Show the ASCII map",
        "tick": "Advance time: tick [n]",
        "history": "Show command history (!n repeats command n)",
        "save": "Save state to JSON: save [file]",
        "load": "Load state from JSON: load [file]",
        "help": "Show this help",
        "quit": "Exit the program (also: exit)",
        "exit": "Exit the program",
    }

    def __init__(self):
        self.history = []

    @staticmethod
    def tokenize(line):
        """Split a line into tokens, tolerating commas and brackets."""
        for ch in ",[]()":
            line = line.replace(ch, " ")
        return line.split()

    def parse(self, line):
        """Parse a command line into ``(command, args)``."""
        line = (line or "").strip()
        if not line:
            return "", []
        if line.startswith("!") and line[1:].isdigit():
            idx = int(line[1:])
            if 1 <= idx <= len(self.history):
                line = self.history[idx - 1]
            else:
                return "invalid_history", []
        self.history.append(line)
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        tokens = self.tokenize(line)
        if not tokens:
            return "", []
        cmd = tokens[0].lower()
        cmd = self.SHORTCUTS.get(cmd, cmd)
        return cmd, tokens[1:]

    def read_command(self, prompt="> "):
        """Read and parse a command from stdin."""
        return self.parse(input(prompt))

    @staticmethod
    def validate_coordinates(tokens):
        """Validate four integer coordinates in 0-800.

        :raises ValueError: with a user friendly message.
        """
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y (got %d)" % len(tokens))
        values = []
        for t in tokens:
            try:
                v = int(str(t))
            except ValueError:
                raise ValueError("'%s' is not an integer" % t)
            if v < 0 or v > config.MAP_SIZE:
                raise ValueError("Coordinate %d out of range 0-%d"
                                 % (v, config.MAP_SIZE))
            values.append(v)
        return values

    def help_text(self):
        """Formatted help text."""
        lines = ["Commands:"]
        for cmd, desc in self.COMMANDS.items():
            short = [k for k, v in self.SHORTCUTS.items() if v == cmd]
            lines.append("  %-8s %-10s %s" % (cmd, ",".join(short), desc))
        return "\n".join(lines)
