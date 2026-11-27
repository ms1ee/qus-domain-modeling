"""Command parsing, input validation and command history."""

from config import SETTINGS

COMMAND_ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "q": "quit",
    "x": "exit",
    "hist": "history",
}

COORDINATE_NAMES = (
    "restaurant x",
    "restaurant y",
    "customer x",
    "customer y",
)


class InputManager:
    """Reads lines, parses commands, validates input and keeps history.

    Args:
        reader: Callable used to read a line (defaults to ``input``); it is
            injectable to make the class testable.
        max_history: Maximum number of remembered commands.
    """

    def __init__(self, reader=None, max_history=200):
        self._reader = reader or input
        self._history = []
        self._max_history = max_history

    @property
    def history(self):
        """list[str]: A copy of the command history, oldest first."""
        return list(self._history)

    def read_line(self, prompt="> "):
        """Read one line of user input.

        Args:
            prompt: Prompt text.

        Returns:
            str or None: The line, or None on end of input.
        """
        try:
            return self._reader(prompt)
        except EOFError:
            return None

    def add_history(self, line):
        """Remember a command, trimming the oldest entries when full.

        Args:
            line: Command text.
        """
        self._history.append(line)
        if len(self._history) > self._max_history:
            del self._history[0]

    def expand_history(self, line):
        """Expand history shortcuts ``!!`` and ``!N``.

        Args:
            line: Raw input line.

        Returns:
            str: The expanded command, or the line unchanged.

        Raises:
            ValueError: If the history reference is invalid.
        """
        if not line.startswith("!"):
            return line
        token = line[1:].strip()
        if not self._history:
            raise ValueError("No command history to reuse.")
        if token in ("", "!"):
            return self._history[-1]
        if token.isdigit():
            index = int(token)
            if 1 <= index <= len(self._history):
                return self._history[index - 1]
            raise ValueError(f"History entry {index} does not exist.")
        raise ValueError(f"Unknown history reference '{line}'.")

    @staticmethod
    def parse_command(line):
        """Split a command line into a canonical name and arguments.

        Args:
            line: Command text.

        Returns:
            tuple: ``(name, args)``; name is "" for an empty line.
        """
        tokens = line.strip().split()
        if not tokens:
            return "", []
        name = tokens[0].lower()
        name = COMMAND_ALIASES.get(name, name)
        return name, tokens[1:]

    @staticmethod
    def validate_coordinate(name, value):
        """Check that a coordinate lies in the map range.

        Args:
            name: Human-readable coordinate name for error messages.
            value: Integer value.

        Returns:
            int: The validated value.

        Raises:
            ValueError: If the value is outside 0-map_size.
        """
        size = SETTINGS["map_size"]
        if not 0 <= value <= size:
            raise ValueError(f"{name} = {value} is out of range 0-{size}.")
        return value

    @classmethod
    def parse_value(cls, name, token):
        """Parse and validate one coordinate token.

        Args:
            name: Coordinate name for messages.
            token: Text to parse.

        Returns:
            int: The integer coordinate.

        Raises:
            ValueError: If the token is not an integer or is out of range.
        """
        try:
            value = int(str(token).strip())
        except ValueError:
            raise ValueError(
                f"{name} must be an integer, got '{token}'.") from None
        return cls.validate_coordinate(name, value)

    @classmethod
    def parse_coordinates(cls, tokens):
        """Parse exactly four coordinate tokens.

        Args:
            tokens: List of four strings.

        Returns:
            list[int]: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the count, type or range is wrong.
        """
        if len(tokens) != 4:
            raise ValueError(
                f"Expected 4 coordinates (restaurant x y, customer x y) "
                f"but got {len(tokens)}.")
        return [cls.parse_value(name, tok)
                for name, tok in zip(COORDINATE_NAMES, tokens)]

    def prompt_coordinates(self):
        """Interactively ask for the four coordinates, re-prompting on errors.

        Returns:
            list[int]: Validated coordinates.

        Raises:
            EOFError: If input ends during prompting.
        """
        values = []
        for name in COORDINATE_NAMES:
            while True:
                raw = self.read_line(f"  {name} (0-{SETTINGS['map_size']}): ")
                if raw is None:
                    raise EOFError
                try:
                    values.append(self.parse_value(name, raw))
                    break
                except ValueError as exc:
                    print(f"Invalid input: {exc}")
        return values
