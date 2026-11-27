"""Command parsing, shortcut resolution, history and input validation."""

from typing import Callable, List, Tuple

COMMANDS = {
    "start": "start",
    "s": "start",
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
    "load": "load",
    "history": "history",
    "hist": "history",
    "help": "help",
    "h": "help",
    "?": "help",
    "quit": "quit",
    "exit": "quit",
    "q": "quit",
}

COORD_LABELS = ["restaurant x", "restaurant y", "customer x", "customer y"]


class InputManager:
    """Parses user commands and validates coordinate input.

    Supports shortcut aliases, command history, '!!' (repeat last command)
    and '!n' (repeat command number n).
    """

    MIN_COORD = 0
    MAX_COORD = 1000

    HELP_TEXT = (
        "Commands:\n"
        "  start [rx ry cx cy]  (s)  Place an order; restaurant then customer coordinates (0-1000)\n"
        "  status               (st) Show funds, riders and their orders\n"
        "  orders               (o)  Show all orders\n"
        "  riders               (r)  Show every rider status change\n"
        "  map                  (m)  Show the ASCII map\n"
        "  tick [n]             (t)  Advance the simulation by n ticks (default 1)\n"
        "  save [file]          Save state to JSON (default dispatch_state.json)\n"
        "  load [file]          Load state from JSON\n"
        "  history              List previously entered commands\n"
        "  !! / !n              Repeat the last command / command number n\n"
        "  help                 (h, ?) Show this help\n"
        "  quit                 (q)  Exit (exit also works)"
    )

    def __init__(self) -> None:
        """Create an input manager with empty history."""
        self._history: List[str] = []

    @property
    def history(self) -> List[str]:
        """Return a copy of the command history."""
        return list(self._history)

    def record(self, line: str) -> None:
        """Add a command to the history.

        Args:
            line: Command line entered by the user.
        """
        self._history.append(line)

    def expand_history(self, line: str) -> str:
        """Resolve '!!' and '!n' history references.

        Args:
            line: Raw user input.

        Returns:
            The command to execute.

        Raises:
            ValueError: If the referenced history entry does not exist.
        """
        if line == "!!":
            if not self._history:
                raise ValueError("there is no previous command to repeat")
            return self._history[-1]
        if line.startswith("!") and line[1:].isdigit():
            index = int(line[1:])
            if not 1 <= index <= len(self._history):
                raise ValueError(f"no history entry number {index}")
            return self._history[index - 1]
        return line

    def parse_command(self, line: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command name and arguments.

        Args:
            line: Command line text.

        Returns:
            Tuple of (canonical command name, argument tokens).

        Raises:
            ValueError: If the command is empty or unknown.
        """
        tokens = line.split()
        if not tokens:
            raise ValueError("empty command")
        name = tokens[0].lower()
        if name not in COMMANDS:
            raise ValueError(f"unknown command '{tokens[0]}'. Type 'help' for a list of commands.")
        return COMMANDS[name], tokens[1:]

    @staticmethod
    def parse_integer(text: str, label: str = "value") -> int:
        """Convert ``text`` to an integer with a clear error message.

        Args:
            text: Text to convert.
            label: Name used in the error message.

        Returns:
            Parsed integer.

        Raises:
            ValueError: If the text is not an integer.
        """
        try:
            return int(str(text).strip())
        except ValueError:
            raise ValueError(f"{label} must be an integer, got '{text}'") from None

    def validate_coordinate(self, value: int, label: str) -> int:
        """Check that a coordinate lies within 0-1000.

        Args:
            value: Integer coordinate.
            label: Name used in the error message.

        Returns:
            The validated value.

        Raises:
            ValueError: If the value is out of range.
        """
        if not self.MIN_COORD <= value <= self.MAX_COORD:
            raise ValueError(
                f"{label} must be between {self.MIN_COORD} and {self.MAX_COORD}, got {value}"
            )
        return value

    def parse_coordinates(self, tokens: List[str]) -> List[int]:
        """Parse four coordinate tokens into a validated list.

        Args:
            tokens: Exactly four tokens: restaurant x, y, customer x, y.

        Returns:
            List of four validated integers.

        Raises:
            ValueError: On wrong token count, non-integer or out-of-range values.
        """
        if len(tokens) != 4:
            raise ValueError(
                f"expected 4 coordinates (restaurant x y, customer x y), got {len(tokens)}"
            )
        coords = []
        for label, token in zip(COORD_LABELS, tokens):
            value = self.parse_integer(token, label)
            coords.append(self.validate_coordinate(value, label))
        return coords

    def read_coordinates(
        self, input_func: Callable[[str], str], output_func: Callable[[str], None] = print
    ) -> List[int]:
        """Prompt for the four coordinates, re-asking on invalid entries.

        Args:
            input_func: Function used to read a line (usually ``input``).
            output_func: Function used to show error messages.

        Returns:
            List of four validated integers.
        """
        coords: List[int] = []
        for label in COORD_LABELS:
            while True:
                text = input_func(f"{label} (0-1000): ")
                try:
                    value = self.parse_integer(text, label)
                    coords.append(self.validate_coordinate(value, label))
                    break
                except ValueError as exc:
                    output_func(f"Error: {exc}. Please try again.")
        return coords
