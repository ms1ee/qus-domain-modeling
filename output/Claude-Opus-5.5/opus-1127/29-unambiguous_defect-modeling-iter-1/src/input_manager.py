"""Command parsing and input validation."""

import re

try:  # command-line history/editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

from path_planner import MAP_SIZE

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "q": "quit", "exit": "quit", "h": "help", "?": "help",
    "m": "map", "n": "step", "hist": "history",
}
COMMANDS = {"start", "status", "orders", "riders", "quit", "help", "map",
            "step", "history", "save"}


class InputError(ValueError):
    """Raised for invalid user input."""


class InputManager:
    """Reads commands, keeps history and validates input."""

    def __init__(self, input_func=input):
        self.command_history = []
        self._input = input_func

    def read_raw(self, prompt=""):
        """Read a raw line from the user."""
        return self._input(prompt)

    def read_command(self, prompt="dispatch> "):
        return self.read_raw(prompt)

    def parse_command(self, line):
        """Parse a command line into ``(command, args)``.

        Supports shortcuts and history recall (``!!`` and ``!N``).
        Returns ``(None, [])`` for empty input and ``("unknown", [word])``
        for unknown commands.
        """
        line = (line or "").strip()
        if not line:
            return None, []
        if line.startswith("!"):
            if line == "!!":
                if not self.command_history:
                    raise InputError("No command history yet.")
                line = self.command_history[-1]
            else:
                try:
                    n = int(line[1:])
                    line = self.command_history[n - 1]
                except (ValueError, IndexError):
                    raise InputError("No such history entry: %s" % line)
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        parts = line.split()
        word = parts[0].lower()
        cmd = SHORTCUTS.get(word, word)
        if cmd not in COMMANDS:
            return "unknown", [word]
        return cmd, parts[1:]

    @staticmethod
    def parse_order_input(text):
        """Validate order input and return 4 ints in range 0-800.

        Accepts ``"1 2 3 4"``, ``"1,2,3,4"`` or ``"[1, 2, 3, 4]"`` (or a list
        of tokens).
        """
        if isinstance(text, (list, tuple)):
            text = " ".join(str(t) for t in text)
        cleaned = re.sub(r"[\[\],]", " ", str(text)).split()
        if len(cleaned) != 4:
            raise InputError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for tok in cleaned:
            try:
                values.append(int(tok))
            except ValueError:
                raise InputError("'%s' is not an integer." % tok)
        for v in values:
            if not 0 <= v <= MAP_SIZE:
                raise InputError("Coordinate %d out of range (0-%d)." % (v, MAP_SIZE))
        return values

    @staticmethod
    def parse_positive_int(text, default=1, maximum=10000):
        """Parse a positive integer argument."""
        if text is None:
            return default
        try:
            value = int(text)
        except ValueError:
            raise InputError("'%s' is not an integer." % text)
        if value < 1 or value > maximum:
            raise InputError("Value must be between 1 and %d." % maximum)
        return value
