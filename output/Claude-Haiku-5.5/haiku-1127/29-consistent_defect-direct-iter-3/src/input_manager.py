"""Command-line parsing, validation and history management."""

from typing import Callable, List, Tuple

from config import INPUT_MAX, INPUT_MIN


class CommandError(ValueError):
    """Raised when user input cannot be parsed or validated."""


COMMAND_ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
    "hist": "history",
}

KNOWN_COMMANDS = {
    "start", "status", "orders", "riders", "map", "tick",
    "save", "history", "help", "quit", "exit",
}

COORD_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")
MAX_TICK_REQUEST = 10000
HISTORY_LIMIT = 50


class InputManager:
    """Reads, parses and validates user commands.

    Attributes:
        history: Previously entered command lines (most recent last).
    """

    PROMPT = "dispatch> "

    def __init__(self, reader: Callable[[str], str] = input,
                 writer: Callable[[str], None] = print) -> None:
        """Create the manager.

        Args:
            reader: Function used to read a line (defaults to ``input``).
            writer: Function used to output text (defaults to ``print``).
        """
        self._reader = reader
        self._writer = writer
        self.history: List[str] = []

    def read_line(self, prompt: str = PROMPT) -> str:
        """Read one raw line from the user."""
        return self._reader(prompt)

    def read_command(self) -> Tuple[str, List[str]]:
        """Read and parse one command line.

        Returns:
            Tuple ``(command_name, arguments)``. An empty line returns
            ``("", [])``.

        Raises:
            CommandError: On unknown commands or invalid shortcuts.
        """
        return self.parse_line(self.read_line())

    def parse_line(self, line: str) -> Tuple[str, List[str]]:
        """Parse a command line, resolving aliases and history shortcuts.

        Args:
            line: Raw input text.

        Returns:
            Tuple ``(command_name, arguments)``.

        Raises:
            CommandError: If the command is unknown or a history reference
                is invalid.
        """
        stripped = line.strip()
        if not stripped:
            return "", []
        if stripped == "!!":
            if not self.history:
                raise CommandError("no previous command in history")
            stripped = self.history[-1]
        elif stripped.startswith("!"):
            index_text = stripped[1:]
            if not index_text.isdigit():
                raise CommandError(f"invalid history reference '{stripped}'")
            index = int(index_text)
            if index < 1 or index > len(self.history):
                raise CommandError(f"history entry {index} does not exist")
            stripped = self.history[index - 1]

        tokens = stripped.split()
        token = tokens[0].lower()
        name = COMMAND_ALIASES.get(token, token)
        if name not in KNOWN_COMMANDS:
            raise CommandError(f"unknown command '{tokens[0]}'. Type 'help' for commands")
        self.history.append(stripped)
        if len(self.history) > HISTORY_LIMIT:
            del self.history[0]
        return name, tokens[1:]

    @staticmethod
    def validate_coordinate(value: int, label: str = "coordinate") -> int:
        """Validate that a coordinate is within the accepted input range.

        Args:
            value: Parsed integer.
            label: Name used in error messages.

        Returns:
            The validated value.

        Raises:
            CommandError: If the value is outside 0-1000.
        """
        if value < INPUT_MIN or value > INPUT_MAX:
            raise CommandError(
                f"{label} {value} is out of range ({INPUT_MIN}-{INPUT_MAX})")
        return value

    def parse_coordinates(self, tokens: List[str]) -> List[int]:
        """Parse exactly four integer coordinates.

        Args:
            tokens: Textual tokens: restaurant x, restaurant y, customer x,
                customer y.

        Returns:
            List of four validated integers.

        Raises:
            CommandError: If the count or the types/ranges are invalid.
        """
        if len(tokens) != 4:
            raise CommandError(
                "expected 4 integers: restaurant_x restaurant_y customer_x customer_y")
        values: List[int] = []
        for label, token in zip(COORD_LABELS, tokens):
            try:
                number = int(token)
            except ValueError:
                raise CommandError(f"{label} '{token}' is not an integer") from None
            values.append(self.validate_coordinate(number, label))
        return values

    def prompt_order(self) -> List[int]:
        """Interactively ask for the four order coordinates.

        Invalid entries are reported and the prompt repeats.

        Returns:
            List of four validated integers.
        """
        values: List[int] = []
        for label in COORD_LABELS:
            while True:
                raw = self.read_line(f"{label} ({INPUT_MIN}-{INPUT_MAX}): ")
                try:
                    number = int(raw.strip())
                    values.append(self.validate_coordinate(number, label))
                    break
                except ValueError as exc:
                    self._writer(f"Invalid input: {exc}. Please try again.")
        return values

    @staticmethod
    def parse_tick_count(tokens: List[str]) -> int:
        """Parse the optional tick count argument of the ``tick`` command.

        Args:
            tokens: Arguments following ``tick``.

        Returns:
            Number of ticks (1 when omitted).

        Raises:
            CommandError: If the value is not a positive integer within limits.
        """
        if not tokens:
            return 1
        try:
            count = int(tokens[0])
        except ValueError:
            raise CommandError(f"tick count '{tokens[0]}' is not an integer") from None
        if count < 1 or count > MAX_TICK_REQUEST:
            raise CommandError(f"tick count must be between 1 and {MAX_TICK_REQUEST}")
        return count
