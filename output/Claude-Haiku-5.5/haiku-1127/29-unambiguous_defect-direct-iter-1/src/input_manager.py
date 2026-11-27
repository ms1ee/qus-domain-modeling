"""Command parsing, shortcut handling and input validation."""

import re

import config

COORD_PATTERN = re.compile(r"[+-]?\d+")
SEPARATOR_PATTERN = re.compile(r"[\s,]+")

SHORTCUTS = {
    "n": "start",
    "s": "status",
    "o": "orders",
    "r": "riders",
    "t": "tick",
    "m": "map",
    "v": "save",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
}

MIN_COORD = 0
MAX_COORD = config.GRID_SIZE


class InputManager:
    """Read user commands and validate coordinate input."""

    def __init__(self, reader=input):
        """Create an input manager.

        Args:
            reader: Callable used to read a line; defaults to ``input``.
        """
        self._reader = reader
        self.history = []

    def enable_history(self):
        """Enable line editing and command recall when ``readline`` exists.

        Returns:
            bool: True if readline support was enabled.
        """
        try:
            import readline  # noqa: F401  (imported for its side effects)
        except ImportError:
            return False
        try:
            readline.set_history_length(200)
        except (AttributeError, OSError):
            return False
        return True

    def read_command(self, prompt="dispatch> "):
        """Read one stripped command line and remember it in history.

        Args:
            prompt: Prompt text shown to the user.

        Returns:
            str: The stripped input line (possibly empty).
        """
        line = self._reader(prompt).strip()
        if line:
            self.history.append(line)
        return line

    @staticmethod
    def parse_command(line):
        """Split a command line into a normalised command and arguments.

        Shortcut letters (for example ``s`` for status) are expanded.

        Args:
            line: Raw command text.

        Returns:
            tuple: ``(command, args)`` where command is lowercase and args is a
            list of strings.
        """
        parts = line.split()
        if not parts:
            return "", []
        token = parts[0].lower()
        return SHORTCUTS.get(token, token), parts[1:]

    @staticmethod
    def validate_coordinate(value):
        """Validate that a value is an integer within 0-800.

        Args:
            value: An int, or a string holding an integer.

        Returns:
            int: The validated coordinate.

        Raises:
            ValueError: If the value is not an integer or is out of range.
        """
        if isinstance(value, bool):
            raise ValueError(f"'{value}' is not an integer")
        if isinstance(value, int):
            number = value
        else:
            text = str(value).strip()
            if not COORD_PATTERN.fullmatch(text):
                raise ValueError(f"'{text}' is not an integer")
            number = int(text)
        if not MIN_COORD <= number <= MAX_COORD:
            raise ValueError(
                f"coordinate {number} is out of range {MIN_COORD}-{MAX_COORD}"
            )
        return number

    @classmethod
    def parse_coordinates(cls, text):
        """Parse exactly four integer coordinates separated by spaces or commas.

        Args:
            text: Raw text such as ``"100 200 300 400"``.

        Returns:
            list[int]: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the count or any value is invalid.
        """
        tokens = [t for t in SEPARATOR_PATTERN.split(text.strip()) if t]
        if len(tokens) != 4:
            raise ValueError(f"expected 4 integer coordinates, got {len(tokens)}")
        return [cls.validate_coordinate(token) for token in tokens]

    def prompt_coordinates(self):
        """Interactively ask for the four order coordinates.

        Returns:
            list[int] or None: The validated coordinates, or None if the user
            cancelled by entering an empty line.
        """
        labels = ["restaurant x", "restaurant y", "customer x", "customer y"]
        print(f"Enter coordinates ({MIN_COORD}-{MAX_COORD}); empty line cancels.")
        values = []
        for label in labels:
            while True:
                raw = self._reader(f"  {label}: ").strip()
                if not raw:
                    return None
                try:
                    values.append(self.validate_coordinate(raw))
                    break
                except ValueError as exc:
                    print(f"    Invalid input: {exc}. Try again.")
        return values
