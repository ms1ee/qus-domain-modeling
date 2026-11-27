"""Command parsing, shortcut resolution, command history and input validation."""

from typing import Callable, List, Optional, Sequence, Tuple

MAP_MIN = 0
MAP_MAX = 800
COORDINATE_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")


class InputManager:
    """Reads and validates user commands.

    Attributes:
        commandHistory: Every accepted command in entry order.
    """

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
        "x": "exit",
        "hist": "history",
    }

    def __init__(self) -> None:
        """Create an input manager with an empty history."""
        self.commandHistory: List[str] = []

    def read_command(self, input_func: Callable[[str], str] = input) -> Optional[str]:
        """Read one raw command line.

        Supports the '!!' shortcut which repeats the last command.

        Args:
            input_func: Function used to read input (injectable for testing).

        Returns:
            The command text, or None for an empty line.

        Raises:
            ValueError: If '!!' is used without any previous command.
        """
        raw = input_func("dispatch> ").strip()
        if not raw:
            return None
        if raw == "!!":
            if not self.commandHistory:
                raise ValueError("no previous command to repeat")
            raw = self.commandHistory[-1]
            print(f"Repeating: {raw}")
        self.commandHistory.append(raw)
        return raw

    def parse_command(self, line: str) -> Tuple[str, List[str]]:
        """Split a command line into its name and arguments.

        Args:
            line: Raw command text.

        Returns:
            Tuple (command_name, argument_list) with shortcuts resolved.

        Raises:
            ValueError: If the line is empty.
        """
        tokens = line.split()
        if not tokens:
            raise ValueError("empty command")
        name = tokens[0].lower()
        return self.ALIASES.get(name, name), tokens[1:]

    def parse_coordinates(self, tokens: Sequence[str]) -> List[int]:
        """Validate four integer coordinates in the range 0-800.

        Args:
            tokens: Exactly four string tokens.

        Returns:
            List of four ints [restaurant_x, restaurant_y, customer_x, customer_y].

        Raises:
            ValueError: If the count, type or range is invalid.
        """
        if len(tokens) != 4:
            raise ValueError(f"expected 4 integers, got {len(tokens)}")
        values: List[int] = []
        for label, token in zip(COORDINATE_LABELS, tokens):
            try:
                value = int(token)
            except ValueError:
                raise ValueError(f"{label} must be an integer, got '{token}'") from None
            if not MAP_MIN <= value <= MAP_MAX:
                raise ValueError(f"{label} must be in range {MAP_MIN}-{MAP_MAX}, got {value}")
            values.append(value)
        return values

    def prompt_coordinates(self, input_func: Callable[[str], str] = input) -> Optional[List[int]]:
        """Interactively ask for the four order coordinates.

        Args:
            input_func: Function used to read input.

        Returns:
            Validated coordinates, or None if the user cancelled.
        """
        print("Enter: restaurant_x restaurant_y customer_x customer_y (0-800), "
              "or 'cancel' to abort.")
        while True:
            raw = input_func("coordinates> ").strip()
            if raw.lower() in ("cancel", "c"):
                return None
            tokens = raw.replace(",", " ").split()
            try:
                return self.parse_coordinates(tokens)
            except ValueError as exc:
                print(f"Invalid input: {exc}. Try again or type 'cancel'.")
