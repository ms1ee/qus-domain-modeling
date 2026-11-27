"""Command parsing and input validation."""

import re

try:  # command history / line editing when available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

COMMANDS = ("start", "status", "orders", "riders", "map", "tick",
            "save", "history", "help", "quit", "exit")

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "m": "map", "t": "tick", "h": "help", "?": "help",
    "hist": "history", "q": "quit", "x": "exit",
}


class InputManager:
    """Parses user commands and validates coordinates."""

    MIN_COORD = 0
    MAX_COORD = 800

    def __init__(self, reader=input):
        self.reader = reader
        self.history = []

    def parse(self, line):
        """Parse a command line into ``(command, args)``.

        Supports shortcuts, ``!!`` (repeat last) and ``!n`` (repeat the
        n-th history entry). Returns ``(None, [])`` for empty input.
        Raises ValueError for unknown commands.
        """
        line = (line or "").strip()
        if not line:
            return None, []
        if line == "!!":
            if not self.history:
                raise ValueError("history is empty")
            line = self.history[-1]
        elif re.fullmatch(r"!\d+", line):
            n = int(line[1:])
            if n < 1 or n > len(self.history):
                raise ValueError(f"no history entry {n}")
            line = self.history[n - 1]
        tokens = line.split(None, 1)
        cmd = tokens[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        if cmd not in COMMANDS:
            raise ValueError(f"unknown command '{tokens[0]}' "
                             "(type 'help')")
        self.history.append(line)
        args = tokens[1].strip() if len(tokens) > 1 else ""
        return cmd, args

    @classmethod
    def parse_coordinates(cls, text):
        """Parse ``[rx, ry, cx, cy]`` from text.

        Accepts separators of spaces/commas and optional brackets.
        Raises ValueError with a helpful message on invalid input.
        """
        if isinstance(text, (list, tuple)):
            tokens = [str(t) for t in text]
        else:
            cleaned = str(text).strip().strip("[]()")
            tokens = [t for t in re.split(r"[\s,]+", cleaned) if t]
        if len(tokens) != 4:
            raise ValueError("please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x "
                             "customer_y")
        values = []
        for t in tokens:
            try:
                values.append(int(t))
            except ValueError:
                raise ValueError(f"'{t}' is not an integer") from None
        for v in values:
            if v < cls.MIN_COORD or v > cls.MAX_COORD:
                raise ValueError(f"coordinate {v} out of range "
                                 f"{cls.MIN_COORD}-{cls.MAX_COORD}")
        return values

    @staticmethod
    def parse_tick_count(text):
        """Parse an optional positive tick count (default 1)."""
        text = (text or "").strip()
        if not text:
            return 1
        try:
            n = int(text)
        except ValueError:
            raise ValueError("tick count must be an integer") from None
        if n < 1 or n > 100000:
            raise ValueError("tick count must be between 1 and 100000")
        return n

    def read(self, prompt):
        """Read a line from the user."""
        return self.reader(prompt)
