"""Command parsing, input validation and command history."""

import re

try:  # optional line editing / history support
    import readline  # noqa: F401  pylint: disable=unused-import
    _HAS_READLINE = True
except ImportError:  # pragma: no cover - platform dependent
    _HAS_READLINE = False


class InputManager:
    """Parses user commands and validates order input."""

    ALIASES = {
        "start": "start", "n": "start", "new": "start",
        "status": "status", "s": "status",
        "orders": "orders", "o": "orders",
        "riders": "riders", "r": "riders",
        "map": "map", "m": "map",
        "tick": "tick", "t": "tick",
        "run": "run",
        "history": "history", "h": "history",
        "save": "save",
        "help": "help", "?": "help",
        "quit": "quit", "exit": "quit", "q": "quit",
    }

    def __init__(self, max_history=500):
        self.command_history = []
        self.max_history = max_history
        self.has_readline = _HAS_READLINE

    def read_command(self, prompt="> "):
        """Read a line from the user and record it in history."""
        line = input(prompt)
        self.remember(line)
        return line

    def remember(self, line):
        """Add a non-empty line to history (bounded)."""
        line = line.strip()
        if line:
            self.command_history.append(line)
            if len(self.command_history) > self.max_history:
                del self.command_history[0]

    def parse(self, line):
        """Parse ``line`` into ``(command, args)``. Unknown commands -> ('unknown', [word])."""
        parts = line.strip().split(None, 1)
        if not parts:
            return "", []
        word = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        command = self.ALIASES.get(word)
        if command is None:
            return "unknown", [parts[0]]
        args = [a for a in re.split(r"[\s,\[\]()]+", rest) if a]
        return command, args

    @staticmethod
    def parse_coordinates(value):
        """Validate order input.

        Accepts a string like ``"100 100 300 300"`` / ``"[100,100,300,300]"`` or
        a list of tokens. Returns a list of 4 ints in range 0-800.

        Raises:
            ValueError: with a user-friendly message.
        """
        if isinstance(value, str):
            tokens = [t for t in re.split(r"[\s,\[\]()]+", value) if t]
        else:
            tokens = list(value)
        if len(tokens) != 4:
            raise ValueError(f"expected 4 integers, got {len(tokens)}")
        coords = []
        for token in tokens:
            try:
                number = int(str(token).strip())
            except ValueError:
                raise ValueError(f"'{token}' is not an integer") from None
            if not 0 <= number <= 800:
                raise ValueError(f"coordinate {number} out of range 0-800")
            coords.append(number)
        return coords

    @staticmethod
    def parse_positive_int(token, default=1, maximum=100000):
        """Parse a positive integer argument."""
        if token is None:
            return default
        try:
            number = int(token)
        except ValueError:
            raise ValueError(f"'{token}' is not an integer") from None
        if number < 1 or number > maximum:
            raise ValueError(f"value must be between 1 and {maximum}")
        return number
