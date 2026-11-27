"""Command parsing, validation, shortcuts and command history."""

from typing import Callable, List, Optional, Sequence, Tuple

from config import COORD_MAX, COORD_MIN


class InputError(ValueError):
    """Raised when user input cannot be parsed or fails validation."""


COMMAND_ALIASES = {
    "s": "start",
    "n": "start",
    "start": "start",
    "st": "status",
    "status": "status",
    "o": "orders",
    "orders": "orders",
    "r": "riders",
    "riders": "riders",
    "m": "map",
    "map": "map",
    "t": "tick",
    "tick": "tick",
    "hist": "history",
    "history": "history",
    "h": "help",
    "?": "help",
    "help": "help",
    "q": "quit",
    "quit": "quit",
    "exit": "quit",
}


class InputManager:
    """Reads, expands and validates user commands.

    Attributes:
        command_history: Executed command lines, oldest first.
    """

    MAX_HISTORY = 100

    def __init__(self, reader: Optional[Callable[[str], str]] = None) -> None:
        """Create an input manager.

        Args:
            reader: Callable used to read a line (defaults to ``input``); it
                allows the manager to be driven programmatically.
        """
        self._reader = reader or input
        self.command_history: List[str] = []

    def read_line(self, prompt: str = "> ") -> Optional[str]:
        """Read one line from the user.

        Returns:
            The line, or ``None`` on end of input.
        """
        try:
            return self._reader(prompt)
        except EOFError:
            return None

    def add_history(self, line: str) -> None:
        """Append an executed command to the history, trimming old entries."""
        self.command_history.append(line)
        if len(self.command_history) > self.MAX_HISTORY:
            del self.command_history[0 : len(self.command_history) - self.MAX_HISTORY]

    def expand_history(self, line: str) -> str:
        """Expand history shortcuts.

        ``!!`` repeats the last command and ``!n`` repeats command number n
        (1-based, as shown by the ``history`` command).

        Args:
            line: Raw user input.

        Returns:
            The command line to execute (may be empty).

        Raises:
            InputError: If the history reference is invalid.
        """
        text = line.strip()
        if not text.startswith("!"):
            return text
        body = text[1:]
        if not self.command_history:
            raise InputError("history is empty")
        if body == "!":
            return self.command_history[-1]
        if body.isdigit():
            index = int(body)
            if 1 <= index <= len(self.command_history):
                return self.command_history[index - 1]
            raise InputError(f"no history entry {index}")
        raise InputError(f"unknown history reference '{text}'")

    def parse_command(self, line: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command name and arguments.

        Args:
            line: Command text, already history-expanded.

        Returns:
            ``(command_name, arguments)``.

        Raises:
            InputError: If the command is unknown.
        """
        parts = line.split()
        if not parts:
            return "", []
        name = COMMAND_ALIASES.get(parts[0].lower())
        if name is None:
            raise InputError(f"unknown command '{parts[0]}' (type 'help')")
        return name, parts[1:]

    def parse_coordinates(self, tokens: Sequence[str]) -> List[int]:
        """Validate four integer coordinates.

        Accepts space- or comma-separated input in the form
        ``restaurant_x restaurant_y customer_x customer_y``.

        Args:
            tokens: Argument tokens.

        Returns:
            List of four integers.

        Raises:
            InputError: On wrong count, non-integer values or out-of-range values.
        """
        text = " ".join(tokens).replace(",", " ")
        parts = text.split()
        if len(parts) != 4:
            raise InputError(
                "expected 4 integers: restaurant_x restaurant_y customer_x customer_y"
            )
        values = []
        for part in parts:
            try:
                value = int(part)
            except ValueError:
                raise InputError(f"'{part}' is not an integer")
            if not COORD_MIN <= value <= COORD_MAX:
                raise InputError(
                    f"coordinate {value} is out of range {COORD_MIN}-{COORD_MAX}"
                )
            values.append(value)
        return values

    def prompt_coordinates(self) -> List[int]:
        """Prompt for four coordinates and validate them.

        Returns:
            List of four validated integers.

        Raises:
            InputError: If input ends or is invalid.
        """
        line = self.read_line(
            "Enter restaurant_x restaurant_y customer_x customer_y: "
        )
        if line is None:
            raise InputError("no input received")
        return self.parse_coordinates(line.split())
