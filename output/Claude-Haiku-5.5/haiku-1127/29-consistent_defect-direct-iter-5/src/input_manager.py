"""Command parsing, shortcut resolution, input validation and history."""

import logging

logger = logging.getLogger(__name__)

COORD_MIN = 0
COORD_MAX = 1000
COORD_LABELS = ("restaurant_x", "restaurant_y", "customer_x", "customer_y")

COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "run": "run",
    "save": "save",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}


class InputManager:
    """Reads and validates user input, keeping a command history."""

    def __init__(self, reader=None, history_size=100):
        """Create the input manager.

        Args:
            reader: Callable taking a prompt and returning a line (defaults to input).
            history_size: Maximum number of remembered commands.
        """
        self._reader = reader or input
        self.history = []
        self.history_size = history_size
        self._enable_readline()

    @staticmethod
    def _enable_readline():
        """Enable line editing and up/down history when readline is available."""
        try:
            import readline  # noqa: F401  (side effect: enables history keys)
        except ImportError:
            logger.debug("readline not available; history keys disabled")

    def _remember(self, line):
        """Add a command to the in-memory history."""
        self.history.append(line)
        if len(self.history) > self.history_size:
            del self.history[0]

    def read_line(self, prompt):
        """Read one line from the user and strip surrounding whitespace.

        Args:
            prompt: Prompt string shown to the user.

        Returns:
            The stripped line (may be empty).
        """
        stripped = self._reader(prompt).strip()
        if stripped:
            self._remember(stripped)
        return stripped

    @staticmethod
    def parse_command(line):
        """Resolve a command word (or shortcut) and split its arguments.

        Args:
            line: A non-empty input line.

        Returns:
            Tuple ``(command_name, arguments)``.

        Raises:
            ValueError: If the command is unknown.
        """
        tokens = line.split()
        if not tokens:
            raise ValueError("Empty command.")
        word = tokens[0].lower()
        name = COMMAND_ALIASES.get(word)
        if name is None:
            raise ValueError(f"Unknown command '{word}'. Type 'help' for a command list.")
        return name, tokens[1:]

    @staticmethod
    def parse_integer(text, label):
        """Parse an integer token with a descriptive error message.

        Args:
            text: Token text.
            label: Name of the value, used in the error message.

        Returns:
            The parsed integer.

        Raises:
            ValueError: If the text is not an integer.
        """
        try:
            return int(text)
        except ValueError:
            raise ValueError(f"{label} must be an integer, got '{text}'.") from None

    @staticmethod
    def validate_coordinate(value, label):
        """Check that a coordinate lies within 0-1000.

        Args:
            value: Integer coordinate.
            label: Name of the value, used in the error message.

        Returns:
            The validated value.

        Raises:
            ValueError: If the value is out of range.
        """
        if not COORD_MIN <= value <= COORD_MAX:
            raise ValueError(
                f"{label} must be between {COORD_MIN} and {COORD_MAX}, got {value}."
            )
        return value

    def parse_coordinates(self, tokens):
        """Parse and validate the four order coordinates.

        Args:
            tokens: List of four string tokens.

        Returns:
            List of four validated integers.

        Raises:
            ValueError: On wrong count, non-integer or out-of-range values.
        """
        tokens = list(tokens)
        if len(tokens) != 4:
            raise ValueError(
                "Expected 4 integer coordinates: restaurant_x restaurant_y "
                f"customer_x customer_y (got {len(tokens)})."
            )
        values = []
        for label, token in zip(COORD_LABELS, tokens):
            value = self.parse_integer(token, label)
            values.append(self.validate_coordinate(value, label))
        return values

    def prompt_coordinates(self, prompt):
        """Ask repeatedly for four coordinates until valid input or cancel.

        Args:
            prompt: Prompt text shown to the user.

        Returns:
            List of four validated integers, or None if the user enters nothing.
        """
        while True:
            line = self._reader(prompt).strip()
            if not line:
                return None
            self._remember(line)
            tokens = line.replace(",", " ").split()
            try:
                return self.parse_coordinates(tokens)
            except ValueError as exc:
                print(f"[Error] {exc} Please try again, or press Enter to cancel.")
