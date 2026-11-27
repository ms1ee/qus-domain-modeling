"""Command parsing, shortcuts, history and input validation."""

from typing import List, Sequence, Tuple

MIN_COORD = 0
MAX_COORD = 800
COORD_NAMES = ("restaurant_x", "restaurant_y", "customer_x", "customer_y")

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "c": "check",
    "h": "help",
    "?": "help",
    "q": "quit",
    "e": "exit",
}


class InputManager:
    """Parses user input lines and keeps the command history.

    Attributes:
        command_history: Every executed command line, oldest first.
        last_command: The most recent command line.
    """

    def __init__(self) -> None:
        self.command_history: List[str] = []
        self.last_command: str = ""

    def parse(self, line: str) -> Tuple[str, List[str]]:
        """Parse a raw input line into a command name and arguments.

        Shortcuts:
            ``!!`` repeats the last command. ``!n`` repeats history entry n
            (1-based).

        Args:
            line: Raw text entered by the user.

        Returns:
            Tuple ``(command, args)``. The command is empty for blank input.

        Raises:
            ValueError: If a history shortcut cannot be resolved.
        """
        text = (line or "").strip()
        if not text:
            return "", []

        if text == "!!":
            if not self.last_command:
                raise ValueError("no previous command in history")
            text = self.last_command
        elif text.startswith("!") and text[1:].isdigit():
            index = int(text[1:])
            if not 1 <= index <= len(self.command_history):
                raise ValueError(f"no history entry {index}")
            text = self.command_history[index - 1]

        tokens = text.split()
        command = ALIASES.get(tokens[0].lower(), tokens[0].lower())
        self.command_history.append(text)
        self.last_command = text
        return command, tokens[1:]

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Validate four coordinate tokens.

        Args:
            tokens: Strings for restaurant_x, restaurant_y, customer_x, customer_y.

        Returns:
            The four coordinates as integers.

        Raises:
            ValueError: If the count is wrong, a token is not an integer, or a
                value is outside 0-800.
        """
        if len(tokens) != 4:
            raise ValueError(
                "start needs 4 integers: restaurant_x restaurant_y customer_x customer_y")
        values: List[int] = []
        for name, token in zip(COORD_NAMES, tokens):
            try:
                value = int(token)
            except ValueError:
                raise ValueError(f"{name} must be an integer, got '{token}'") from None
            if not MIN_COORD <= value <= MAX_COORD:
                raise ValueError(
                    f"{name} must be between {MIN_COORD} and {MAX_COORD}, got {value}")
            values.append(value)
        return values
