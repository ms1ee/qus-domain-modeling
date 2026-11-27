"""Command parsing, shortcut expansion, history and input validation."""

from typing import List, Tuple

from order_model import validate_coordinate

try:  # readline gives arrow-key editing and history where available.
    import readline  # noqa: F401  pylint: disable=unused-import
except ImportError:  # pragma: no cover - platform dependent
    readline = None

COMMAND_ALIASES = {
    "start": "start",
    "new": "start",
    "n": "start",
    "status": "status",
    "s": "status",
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
    "help": "help",
    "h": "help",
    "?": "help",
    "quit": "quit",
    "exit": "quit",
    "q": "quit",
}

MAX_HISTORY = 200


class InputManager:
    """Parses user input lines into validated commands.

    Attributes:
        command_history: Previously entered command lines (most recent last).
    """

    def __init__(self) -> None:
        """Create an input manager with an empty history."""
        self.command_history: List[str] = []

    def expand(self, line: str) -> str:
        """Expand shortcut keys such as ``!!`` (repeat last command).

        Args:
            line: Raw input line.

        Returns:
            The expanded line.

        Raises:
            ValueError: If ``!!`` is used with an empty history.
        """
        stripped = line.strip()
        if stripped == "!!":
            if not self.command_history:
                raise ValueError("no previous command to repeat")
            return self.command_history[-1]
        return stripped

    def parse(self, line: str) -> Tuple[str, List[str]]:
        """Split a line into a canonical command name and its arguments.

        Args:
            line: Expanded input line.

        Returns:
            Tuple ``(command, args)``. ``command`` is an empty string for blank input.

        Raises:
            ValueError: If the command is unknown.
        """
        tokens = line.replace(",", " ").split()
        if not tokens:
            return "", []
        name = tokens[0].lower()
        if name not in COMMAND_ALIASES:
            raise ValueError(f"unknown command '{name}'. Type 'help' for the command list")
        return COMMAND_ALIASES[name], tokens[1:]

    def record(self, line: str) -> None:
        """Append a command line to the history (bounded in size).

        Args:
            line: Command line to store.
        """
        if not line.strip():
            return
        self.command_history.append(line.strip())
        if len(self.command_history) > MAX_HISTORY:
            del self.command_history[0]

    @staticmethod
    def parse_coordinates(tokens: List[str]) -> List[int]:
        """Validate four coordinate tokens.

        Args:
            tokens: Strings expected to hold restaurant_x, restaurant_y,
                customer_x and customer_y.

        Returns:
            List of four validated integers.

        Raises:
            ValueError: On wrong token count, non-integer or out-of-range values.
        """
        if len(tokens) != 4:
            raise ValueError(
                "expected 4 integers: restaurant_x restaurant_y customer_x customer_y "
                f"(got {len(tokens)})"
            )
        labels = ["restaurant x", "restaurant y", "customer x", "customer y"]
        values: List[int] = []
        for token, label in zip(tokens, labels):
            try:
                number = int(token)
            except ValueError as exc:
                raise ValueError(f"{label} '{token}' is not an integer") from exc
            values.append(validate_coordinate(number, label))
        return values

    @staticmethod
    def read_line(prompt: str) -> str:
        """Prompt the user for a line of input.

        Args:
            prompt: Prompt text.

        Returns:
            The entered line.
        """
        return input(prompt)
