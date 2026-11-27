"""Command parsing, shortcut resolution and input validation."""

from typing import Callable, List, Optional, Sequence, Tuple

COORDINATE_NAMES = ("restaurant_x", "restaurant_y", "customer_x", "customer_y")
COORDINATE_MIN = 0
COORDINATE_MAX = 800
MAX_HISTORY = 100


class InputError(ValueError):
    """Raised when user input does not satisfy the expected format or range."""


class InputManager:
    """Reads lines, resolves shortcut keys, keeps history and validates input."""

    COMMANDS = (
        "start",
        "status",
        "orders",
        "riders",
        "map",
        "tick",
        "save",
        "history",
        "help",
        "quit",
        "exit",
    )

    SHORTCUTS = {
        "s": "start",
        "t": "status",
        "o": "orders",
        "r": "riders",
        "m": "map",
        "k": "tick",
        "v": "save",
        "y": "history",
        "h": "help",
        "?": "help",
        "q": "quit",
    }

    def __init__(self, reader: Optional[Callable[[str], str]] = None) -> None:
        """Create the input manager.

        Args:
            reader: Callable used to read a line (defaults to ``input``); a
                prompt string is passed to it.
        """
        self._reader = reader or input
        self.history: List[str] = []

    def read_line(self, prompt: str = "> ") -> str:
        """Read one stripped line and remember non-empty entries.

        Args:
            prompt: Prompt text shown to the user.

        Returns:
            The stripped input text (may be empty).
        """
        text = self._reader(prompt).strip()
        if text:
            self.history.append(text)
            if len(self.history) > MAX_HISTORY:
                del self.history[0]
        return text

    @classmethod
    def parse_command(cls, text: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command name and arguments.

        Args:
            text: Raw command line.

        Returns:
            Tuple ``(command, arguments)``; the command is "" for blank input.
        """
        parts = text.strip().split()
        if not parts:
            return "", []
        name = parts[0].lower()
        name = cls.SHORTCUTS.get(name, name)
        return name, parts[1:]

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Parse and validate four integer coordinates.

        Accepts whitespace- or comma-separated values, e.g.
        ``"100 200 300 400"`` or ``"100,200,300,400"``.

        Args:
            tokens: Argument tokens or whole input strings.

        Returns:
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            InputError: If the count, type or range of the values is invalid.
        """
        raw: List[str] = []
        for token in tokens:
            raw.extend(part for part in token.replace(",", " ").split() if part)
        if len(raw) != 4:
            raise InputError(
                "expected 4 integer coordinates: restaurant_x restaurant_y "
                f"customer_x customer_y (got {len(raw)})"
            )
        values: List[int] = []
        for name, token in zip(COORDINATE_NAMES, raw):
            try:
                value = int(token)
            except ValueError as exc:
                raise InputError(f"{name} must be an integer, got '{token}'") from exc
            if not COORDINATE_MIN <= value <= COORDINATE_MAX:
                raise InputError(
                    f"{name} must be in range {COORDINATE_MIN}-{COORDINATE_MAX}, got {value}"
                )
            values.append(value)
        return values

    @staticmethod
    def parse_positive_int(tokens: Sequence[str], default: int, maximum: int) -> int:
        """Parse an optional positive integer argument.

        Args:
            tokens: Argument tokens; the first one is used when present.
            default: Value returned when no argument is given.
            maximum: Upper bound (inclusive).

        Returns:
            The parsed integer.

        Raises:
            InputError: If the value is not an integer within 1..maximum.
        """
        if not tokens:
            return default
        try:
            value = int(tokens[0])
        except ValueError as exc:
            raise InputError(f"expected an integer, got '{tokens[0]}'") from exc
        if not 1 <= value <= maximum:
            raise InputError(f"value must be between 1 and {maximum}, got {value}")
        return value
