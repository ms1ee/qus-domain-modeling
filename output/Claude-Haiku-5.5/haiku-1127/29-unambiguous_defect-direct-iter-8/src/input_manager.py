"""Command parsing, shortcut keys, command history and input validation."""

from typing import List, Sequence, Tuple

from globalvar import MAP_SIZE

try:  # readline gives line editing and history on platforms that provide it.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None  # type: ignore[assignment]


class InputError(ValueError):
    """Raised when user input cannot be parsed or fails validation."""


COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "save": "save",
    "history": "history",
    "help": "help", "?": "help", "h": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}


class InputManager:
    """Reads and validates user commands.

    Attributes:
        history: Recently entered command lines, newest last.
    """

    def __init__(self, max_history: int = 100) -> None:
        """Create the manager.

        Args:
            max_history: Number of command lines kept in memory.
        """
        self.history: List[str] = []
        self._max_history = max_history

    @staticmethod
    def read_line(prompt: str) -> str:
        """Read one line from standard input.

        Args:
            prompt: Prompt text.

        Returns:
            The stripped input line.

        Raises:
            EOFError: At end of input.
        """
        return input(prompt).strip()

    def record(self, line: str) -> None:
        """Remember a command line for the ``history`` command and readline.

        Args:
            line: The command line entered by the user.
        """
        if not line.strip():
            return
        self.history.append(line.strip())
        if len(self.history) > self._max_history:
            del self.history[: len(self.history) - self._max_history]
        if readline is not None:
            try:
                readline.add_history(line.strip())
            except Exception:  # pragma: no cover - defensive
                pass

    @staticmethod
    def parse_command(line: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command name and arguments.

        An empty line maps to ``tick`` with a count of 1.

        Args:
            line: Raw input line.

        Returns:
            Pair ``(command, arguments)``.

        Raises:
            InputError: If the command is unknown.
        """
        parts = line.strip().split()
        if not parts:
            return "tick", ["1"]
        key = parts[0].lower()
        if key not in COMMAND_ALIASES:
            raise InputError(
                f"unknown command '{parts[0]}'. Type 'help' for the command list."
            )
        return COMMAND_ALIASES[key], parts[1:]

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Parse four integer coordinates from user tokens.

        Commas, brackets and spaces are accepted as separators.

        Args:
            tokens: Words entered after the command or at the prompt.

        Returns:
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            InputError: On a wrong count, a non-integer, or an out-of-range value.
        """
        text = " ".join(tokens)
        for separator in ("[", "]", ","):
            text = text.replace(separator, " ")
        cleaned = text.split()
        if len(cleaned) != 4:
            raise InputError(
                "expected 4 integers: restaurant_x restaurant_y customer_x customer_y"
            )
        values: List[int] = []
        for token in cleaned:
            try:
                value = int(token)
            except ValueError:
                raise InputError(f"'{token}' is not an integer") from None
            if not 0 <= value <= MAP_SIZE:
                raise InputError(f"coordinate {value} is out of range 0-{MAP_SIZE}")
            values.append(value)
        return values

    @staticmethod
    def parse_count(tokens: Sequence[str], default: int, maximum: int) -> int:
        """Parse an optional positive count argument.

        Args:
            tokens: Command arguments.
            default: Value used when no argument is given.
            maximum: Largest allowed value.

        Raises:
            InputError: If the argument is not a positive integer within range.
        """
        if not tokens:
            return default
        try:
            count = int(tokens[0])
        except ValueError:
            raise InputError(f"'{tokens[0]}' is not an integer") from None
        if not 1 <= count <= maximum:
            raise InputError(f"count must be between 1 and {maximum}")
        return count
