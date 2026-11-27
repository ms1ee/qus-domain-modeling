"""Command parsing, input validation and command history."""

from collections import deque

try:  # optional line editing / arrow-key history
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "m": "map", "n": "step", "t": "step", "hi": "history",
    "h": "help", "?": "help", "q": "quit", "exit": "quit",
}

COMMANDS = {"start", "status", "orders", "riders", "map", "step",
            "history", "help", "save", "quit"}


class InputManager:
    """Parses commands and validates coordinate input."""

    def __init__(self, max_history=200, min_coord=0, max_coord=800):
        self.command_history = deque(maxlen=max_history)
        self.min_coord = min_coord
        self.max_coord = max_coord

    def read_line(self, prompt="> "):
        """Read a line from stdin (raises EOFError/KeyboardInterrupt)."""
        return input(prompt)

    def resolve_history(self, line):
        """Expand ``!N`` / ``!!`` references to earlier commands."""
        line = line.strip()
        if line == "!!":
            if not self.command_history:
                raise ValueError("no previous command")
            return self.command_history[-1]
        if line.startswith("!"):
            try:
                idx = int(line[1:])
            except ValueError:
                raise ValueError("usage: !N where N is a history number")
            if not 1 <= idx <= len(self.command_history):
                raise ValueError("no such history entry: %d" % idx)
            return self.command_history[idx - 1]
        return line

    def parse_command(self, line):
        """Return ``(command, args)``; unknown commands are returned as-is."""
        line = self.resolve_history(line)
        if not line:
            return "", []
        self.command_history.append(line)
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        args = parts[1] if len(parts) > 1 else ""
        return cmd, args

    def parse_coordinates(self, text):
        """Parse ``[rx, ry, cx, cy]`` into four validated integers.

        :raises ValueError: with a user friendly message.
        """
        cleaned = str(text)
        for ch in "[](),;":
            cleaned = cleaned.replace(ch, " ")
        parts = cleaned.split()
        if len(parts) != 4:
            raise ValueError("exactly 4 integers are required "
                             "(restaurant_x restaurant_y customer_x customer_y)")
        values = []
        for p in parts:
            try:
                v = int(p)
            except ValueError:
                raise ValueError("'%s' is not an integer" % p)
            if not self.min_coord <= v <= self.max_coord:
                raise ValueError("coordinate %d out of range %d-%d" % (
                    v, self.min_coord, self.max_coord))
            values.append(v)
        return values

    def parse_step_count(self, text, maximum=1000):
        """Parse the argument of ``step`` (default 1)."""
        text = str(text).strip()
        if not text:
            return 1
        try:
            n = int(text)
        except ValueError:
            raise ValueError("step count must be an integer")
        if not 1 <= n <= maximum:
            raise ValueError("step count must be between 1 and %d" % maximum)
        return n

    def history_text(self):
        """Numbered command history."""
        if not self.command_history:
            return "No commands yet."
        return "\n".join("%3d  %s" % (i + 1, c)
                         for i, c in enumerate(self.command_history))
