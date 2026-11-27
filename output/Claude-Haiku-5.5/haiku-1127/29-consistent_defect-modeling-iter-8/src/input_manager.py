"""Command parsing, shortcut resolution, history and input validation."""

COORD_MIN = 0
COORD_MAX = 1000


class InputError(ValueError):
    """Raised for malformed or out-of-range user input."""


class InputManager:
    """Reads and validates user commands."""

    SHORTCUTS = {
        "s": "start",
        "st": "status",
        "o": "orders",
        "r": "riders",
        "m": "map",
        "t": "tick",
        "u": "run",
        "h": "help",
        "?": "help",
        "hist": "history",
        "q": "quit",
        "e": "exit",
    }

    def __init__(self):
        """Create the input manager with an empty command history."""
        self.command_history = []

    def read_line(self, prompt="> "):
        """Read one line from standard input.

        Returns:
            The raw line, or "quit" when input is closed.
        """
        try:
            return input(prompt)
        except EOFError:
            return "quit"

    def parse_command(self, line):
        """Split a command line into a normalised name and argument list.

        Supports shortcut keys, "!!" (repeat last command) and "!n" (repeat
        the n-th command from history).

        Args:
            line: Raw input text.

        Returns:
            Tuple (command_name, args). Empty input yields ("", []).

        Raises:
            InputError: If a history reference is invalid.
        """
        stripped = line.strip()
        if not stripped:
            return "", []
        if stripped.startswith("!"):
            ref = stripped[1:]
            if not self.command_history:
                raise InputError("No command history available yet.")
            if ref == "!":
                stripped = self.command_history[-1]
            elif ref.isdigit() and 1 <= int(ref) <= len(self.command_history):
                stripped = self.command_history[int(ref) - 1]
            else:
                raise InputError("Unknown history reference. Use !! or !<number>.")
        self.command_history.append(stripped)
        parts = stripped.split()
        name = parts[0].lower()
        name = self.SHORTCUTS.get(name, name)
        return name, parts[1:]

    def parse_coordinates(self, tokens):
        """Validate four integer coordinates.

        Accepts forms such as ``100 200 300 400`` or ``[100, 200, 300, 400]``.

        Args:
            tokens: Iterable of string tokens.

        Returns:
            Tuple (restaurant_x, restaurant_y, customer_x, customer_y).

        Raises:
            InputError: On wrong count, non-integer values or out-of-range values.
        """
        text = " ".join(tokens)
        for ch in "[](),":
            text = text.replace(ch, " ")
        parts = text.split()
        if len(parts) != 4:
            raise InputError(
                "Expected 4 coordinates: restaurant_x restaurant_y "
                "customer_x customer_y.")
        values = []
        for part in parts:
            try:
                value = int(part)
            except ValueError:
                raise InputError(f"'{part}' is not an integer coordinate.")
            if not COORD_MIN <= value <= COORD_MAX:
                raise InputError(
                    f"Coordinate {value} is out of range "
                    f"{COORD_MIN}-{COORD_MAX}.")
            values.append(value)
        return tuple(values)

    def history(self):
        """Return a copy of the command history list."""
        return list(self.command_history)
