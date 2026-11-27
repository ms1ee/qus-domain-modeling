"""Command parsing, shortcut resolution, history and input validation."""

from typing import List, Optional, Tuple

try:  # Enables line editing and history on platforms that provide readline.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

COORD_MIN = 0
COORD_MAX = 1000
MAX_TICKS_PER_COMMAND = 10000
HISTORY_LIMIT = 200

COORD_LABELS = ("restaurant_x", "restaurant_y", "customer_x", "customer_y")

COMMAND_ALIASES = {
    "start": "start",
    "n": "start",
    "status": "status",
    "st": "status",
    "orders": "orders",
    "o": "orders",
    "riders": "riders",
    "r": "riders",
    "map": "map",
    "m": "map",
    "tick": "tick",
    "t": "tick",
    "save": "save",
    "history": "history",
    "hist": "history",
    "help": "help",
    "h": "help",
    "?": "help",
    "quit": "quit",
    "exit": "quit",
    "q": "quit",
}


class InputError(ValueError):
    """Raised when user input cannot be parsed or fails validation."""


class InputManager:
    """Parses user input lines and validates their arguments.

    Attributes:
        history: Ordered list of accepted command lines (most recent last).
    """

    def __init__(self) -> None:
        """Create an empty command history."""
        self.history: List[str] = []

    def read_line(self, prompt: str) -> Optional[str]:
        """Read one line from standard input.

        Returns:
            The entered text, or None on end-of-file or Ctrl+C.
        """
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            return None

    @staticmethod
    def split_tokens(text: Optional[str]) -> List[str]:
        """Split a line into tokens, treating commas as separators."""
        if not text:
            return []
        return text.replace(",", " ").split()

    def _remember(self, text: str) -> None:
        """Append a command to history, keeping a bounded length."""
        self.history.append(text)
        if len(self.history) > HISTORY_LIMIT:
            del self.history[0]

    def parse_command(self, line: Optional[str]) -> Tuple[str, List[str]]:
        """Parse a command line into a canonical command name and arguments.

        Supports shortcut aliases and ``!!`` to repeat the last command.

        Args:
            line: Raw input line.

        Returns:
            Tuple ``(command, args)``; command is "" for an empty line.

        Raises:
            InputError: If the command is unknown or there is nothing to repeat.
        """
        text = (line or "").strip()
        if not text:
            return "", []
        if text == "!!":
            if not self.history:
                raise InputError("No previous command to repeat.")
            text = self.history[-1]
        tokens = self.split_tokens(text)
        name = tokens[0].lower()
        if name not in COMMAND_ALIASES:
            raise InputError(f"Unknown command '{name}'. Type 'help' for a list of commands.")
        self._remember(text)
        return COMMAND_ALIASES[name], tokens[1:]

    @staticmethod
    def parse_coordinates(tokens: List[str]) -> List[int]:
        """Validate four integer coordinates in the range 0-1000.

        Args:
            tokens: Exactly four tokens in the order restaurant_x, restaurant_y,
                customer_x, customer_y.

        Returns:
            List of four ints.

        Raises:
            InputError: On wrong count, non-integer or out-of-range values.
        """
        if len(tokens) != 4:
            raise InputError(
                "Expected 4 integer coordinates: restaurant_x restaurant_y "
                "customer_x customer_y."
            )
        values: List[int] = []
        for label, token in zip(COORD_LABELS, tokens):
            try:
                value = int(token)
            except ValueError:
                raise InputError(f"{label} must be an integer, got '{token}'.") from None
            if not COORD_MIN <= value <= COORD_MAX:
                raise InputError(
                    f"{label} = {value} is out of range {COORD_MIN}-{COORD_MAX}."
                )
            values.append(value)
        return values

    @staticmethod
    def parse_tick_count(tokens: List[str]) -> int:
        """Parse the optional tick count argument of the ``tick`` command.

        Returns:
            Number of ticks to run (default 1).

        Raises:
            InputError: If the argument is not a positive integer within limits.
        """
        if not tokens:
            return 1
        try:
            count = int(tokens[0])
        except ValueError:
            raise InputError(f"Tick count must be an integer, got '{tokens[0]}'.") from None
        if not 1 <= count <= MAX_TICKS_PER_COMMAND:
            raise InputError(f"Tick count must be between 1 and {MAX_TICKS_PER_COMMAND}.")
        return count
