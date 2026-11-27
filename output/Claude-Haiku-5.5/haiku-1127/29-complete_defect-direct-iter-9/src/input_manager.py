"""Command parsing, shortcut resolution, history and input validation."""

import grid

try:  # Enables arrow-key line editing and history where available.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

COMMANDS = {
    "start", "status", "orders", "riders", "map", "tick", "save",
    "history", "help", "quit", "exit",
}

SHORTCUTS = {
    "a": "start",
    "s": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "v": "save",
    "y": "history",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
}


class InputManager:
    """Read, expand and parse user commands.

    Attributes:
        history: Ordered list of previously entered command lines.
    """

    def __init__(self, reader=input):
        """Create the input manager.

        Args:
            reader: Callable used to read a line, taking a prompt argument.
        """
        self._reader = reader
        self.history = []

    def read_line(self, prompt="dispatch> "):
        """Read one raw line from the user.

        Args:
            prompt: Prompt text.

        Returns:
            str: The stripped input line.
        """
        return self._reader(prompt).strip()

    def record(self, line):
        """Add a non-empty command line to the history."""
        if line.strip():
            self.history.append(line.strip())

    def expand_history(self, line):
        """Expand ``!!`` (last command) and ``!n`` (n-th command) references.

        Args:
            line: Raw command line.

        Returns:
            str: The expanded command line.

        Raises:
            IndexError: If the referenced history entry does not exist.
        """
        stripped = line.strip()
        if stripped == "!!":
            if not self.history:
                raise IndexError("no previous command in history")
            return self.history[-1]
        if stripped.startswith("!") and stripped[1:].isdigit():
            index = int(stripped[1:])
            if index < 1 or index > len(self.history):
                raise IndexError(f"no history entry {index}")
            return self.history[index - 1]
        return stripped

    def parse_command(self, line):
        """Split a command line into a canonical command name and arguments.

        Args:
            line: Expanded command line.

        Returns:
            tuple[str | None, list[str]]: Command name and argument tokens.

        Raises:
            ValueError: If the command is unknown.
        """
        parts = line.split()
        if not parts:
            return None, []
        word = parts[0].lower()
        name = SHORTCUTS.get(word, word)
        if name not in COMMANDS:
            raise ValueError(f"unknown command '{parts[0]}'. Type 'help'.")
        return name, parts[1:]

    @staticmethod
    def parse_coordinate_token(token):
        """Convert one token to a validated integer coordinate.

        Args:
            token: Text token from the user.

        Returns:
            int: The validated coordinate.

        Raises:
            ValueError: If the token is not an integer or is out of range.
        """
        try:
            value = int(token)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"'{token}' is not an integer") from exc
        return grid.validate_coordinate(value)

    def parse_coordinates(self, tokens):
        """Parse four coordinates ``[rx, ry, cx, cy]``.

        Args:
            tokens: Sequence of four text tokens.

        Returns:
            list[int]: Validated coordinates.

        Raises:
            ValueError: If the count is wrong or a value is invalid.
        """
        tokens = list(tokens)
        if len(tokens) != 4:
            raise ValueError("expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y")
        return [self.parse_coordinate_token(token) for token in tokens]

    def prompt_coordinates(self, writer=print):
        """Interactively ask for the four order coordinates.

        Invalid entries are reported and re-requested. Typing ``cancel``
        aborts the order.

        Args:
            writer: Callable used to print messages.

        Returns:
            list[int] | None: Validated coordinates, or None if cancelled.
        """
        labels = ["restaurant x", "restaurant y",
                  "customer x", "customer y"]
        values = []
        for label in labels:
            while True:
                raw = self.read_line(f"  {label} (0-800, 'cancel' to abort): ")
                if raw.lower() == "cancel":
                    return None
                try:
                    values.append(self.parse_coordinate_token(raw))
                    break
                except ValueError as exc:
                    writer(f"  Invalid input: {exc}. Try again.")
        return values
