"""Command parsing, shortcut keys, command history and input validation."""

COMMANDS = (
    "start", "status", "orders", "riders", "tick", "map",
    "save", "help", "quit", "exit",
)

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "t": "tick",
    "m": "map",
    "h": "help",
    "?": "help",
    "q": "quit",
}

COORD_MIN = 0
COORD_MAX = 1000


class InputError(Exception):
    """Raised for malformed or invalid user input."""


class InputManager:
    """Reads and validates user commands.

    Attributes:
        history (list[str]): Executed command lines, oldest first.
    """

    def __init__(self, reader=input):
        """Create the manager.

        Args:
            reader: Callable used to read a line (defaults to ``input``).
        """
        self._reader = reader
        self.history = []

    def read_line(self, prompt="sim> "):
        """Read one line from the user.

        Args:
            prompt: Prompt text.

        Returns:
            str: Stripped input line.

        Raises:
            EOFError: When input is closed.
        """
        return self._reader(prompt).strip()

    def parse(self, line):
        """Parse a command line, handling shortcuts and history recall.

        Supports ``!!`` (repeat last command) and ``!n`` (repeat history entry n).

        Args:
            line: Raw input text.

        Returns:
            tuple[str | None, list[str]]: Command name (None for blank input)
            and its argument tokens.

        Raises:
            InputError: For unknown commands or invalid history references.
        """
        text = line.strip()
        if not text:
            return None, []
        if text == "!!":
            if not self.history:
                raise InputError("No command in history yet.")
            text = self.history[-1]
        elif text.startswith("!") and text[1:].isdigit():
            index = int(text[1:])
            if not 1 <= index <= len(self.history):
                raise InputError("History entry %d does not exist." % index)
            text = self.history[index - 1]

        tokens = text.split()
        name = tokens[0].lower()
        command = ALIASES.get(name, name)
        if command not in COMMANDS:
            raise InputError(
                "Unknown command '%s'. Type 'help' for a list." % tokens[0]
            )
        self.history.append(text)
        return command, tokens[1:]

    @staticmethod
    def parse_int(text, name="value"):
        """Convert text to an integer with a helpful error message.

        Args:
            text: Token to convert.
            name: Field name used in the error message.

        Returns:
            int: Parsed integer.

        Raises:
            InputError: If the text is not an integer.
        """
        try:
            return int(text)
        except (TypeError, ValueError):
            raise InputError("%s must be an integer, got '%s'." % (name, text))

    @classmethod
    def parse_coordinates(cls, tokens):
        """Parse four coordinate tokens.

        Args:
            tokens: Iterable of four strings.

        Returns:
            list[int]: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            InputError: On wrong count, non-integer or out-of-range values.
        """
        tokens = list(tokens)
        if len(tokens) != 4:
            raise InputError(
                "Expected 4 integers: restaurant_x restaurant_y "
                "customer_x customer_y."
            )
        names = ("restaurant_x", "restaurant_y", "customer_x", "customer_y")
        values = [cls.parse_int(t, n) for t, n in zip(tokens, names)]
        for name, value in zip(names, values):
            if not COORD_MIN <= value <= COORD_MAX:
                raise InputError(
                    "%s=%d is out of range (%d-%d)."
                    % (name, value, COORD_MIN, COORD_MAX)
                )
        return values

    def prompt_coordinates(self):
        """Ask the user for four coordinates interactively.

        Returns:
            list[int]: Validated coordinates.

        Raises:
            InputError: On invalid input.
        """
        line = self.read_line(
            "Enter restaurant_x restaurant_y customer_x customer_y: "
        )
        tokens = line.replace(",", " ").split()
        return self.parse_coordinates(tokens)
