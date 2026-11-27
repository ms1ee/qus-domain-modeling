"""Command parsing, shortcut handling, history and input validation."""

import logging

logger = logging.getLogger(__name__)

COORD_MIN = 0
COORD_MAX = 800
COORD_NAMES = ("restaurant x", "restaurant y", "customer x", "customer y")

COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick", "step": "tick", "next": "tick",
    "save": "save",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}


class InputManager:
    """Reads user input, expands history shortcuts and validates values.

    Shortcuts:
        ``!!`` repeats the previous command; ``!n`` repeats history entry n.
    """

    def __init__(self, input_func=input):
        """Create the manager.

        Args:
            input_func: Callable used to read a line (injectable for testing).
        """
        self._input = input_func
        self.history = []

    def read_line(self, prompt="> "):
        """Read one command line, expanding history shortcuts.

        Args:
            prompt: Prompt text.

        Returns:
            The command text (possibly empty).

        Raises:
            ValueError: If a history shortcut cannot be resolved.
        """
        raw = self._input(prompt).strip()
        if not raw:
            return ""
        if raw == "!!":
            if not self.history:
                raise ValueError("no previous command in history")
            raw = self.history[-1]
        elif raw.startswith("!") and raw[1:].isdigit():
            index = int(raw[1:])
            if not 1 <= index <= len(self.history):
                raise ValueError(f"history entry {index} does not exist")
            raw = self.history[index - 1]
        self.history.append(raw)
        return raw

    @staticmethod
    def parse_command(line):
        """Split a command line into a canonical command name and arguments.

        Args:
            line: Raw command text.

        Returns:
            Tuple ``(command, args)``; command is empty for blank input.
        """
        parts = line.split()
        if not parts:
            return "", []
        name = parts[0].lower()
        return COMMAND_ALIASES.get(name, name), parts[1:]

    @staticmethod
    def parse_int(token, name):
        """Parse an integer token with a clear error message.

        Raises:
            ValueError: If the token is not an integer.
        """
        try:
            return int(token)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be an integer, got {token!r}") from None

    @staticmethod
    def validate_coordinate(name, value):
        """Ensure a coordinate lies within the map range.

        Raises:
            ValueError: If the value is outside 0-800.
        """
        if not COORD_MIN <= value <= COORD_MAX:
            raise ValueError(f"{name} must be between {COORD_MIN} and {COORD_MAX}, got {value}")
        return value

    def collect_coordinates(self, tokens):
        """Return four validated coordinates from arguments or prompts.

        Args:
            tokens: Arguments following the ``start`` command. Either empty
                (prompt for each value) or exactly four integers.

        Returns:
            List of four integers in the order restaurant x, y, customer x, y.

        Raises:
            ValueError: If the argument count or values are invalid.
        """
        if tokens:
            if len(tokens) != 4:
                raise ValueError("start expects 4 integers: restaurant_x restaurant_y "
                                 "customer_x customer_y")
            return [self.validate_coordinate(name, self.parse_int(token, name))
                    for token, name in zip(tokens, COORD_NAMES)]

        values = []
        print(f"Enter coordinates in the range {COORD_MIN}-{COORD_MAX}:")
        for name in COORD_NAMES:
            while True:
                raw = self._input(f"  {name}: ").strip()
                try:
                    value = self.validate_coordinate(name, self.parse_int(raw, name))
                except ValueError as exc:
                    print(f"Error: {exc}")
                    continue
                values.append(value)
                break
        return values
