"""Command parsing, shortcut resolution, history and input validation."""

from typing import Callable, List, Tuple

from path_planner import MAX_INPUT_COORD

COMMANDS = {"start", "status", "orders", "riders", "map", "tick",
            "history", "help", "quit"}

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "hist": "history",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "quit",
    "exit": "quit",
}

COORD_LABELS = ["restaurant x", "restaurant y", "customer x", "customer y"]


class InputManager:
    """Reads, parses and validates user commands.

    Supports shortcut keys (see ``ALIASES``), command history, ``!!`` to repeat
    the last command and ``!n`` to repeat history entry n.
    """

    def __init__(self, reader: Callable[[str], str] = input) -> None:
        """Create an input manager.

        Args:
            reader: Function used to read a line. Defaults to ``input``.
        """
        self._reader = reader
        self._history: List[str] = []

    @property
    def history(self) -> List[str]:
        """A copy of the command history."""
        return list(self._history)

    def read_command(self, prompt: str = "dispatch> ") -> Tuple[str, List[str]]:
        """Read one line and parse it into a command and arguments.

        Args:
            prompt: Prompt shown to the user.

        Returns:
            ``(command, args)``. Command is "" for an empty line.

        Raises:
            ValueError: For unknown commands or invalid history references.
            EOFError: If input is closed.
        """
        line = self._reader(prompt).strip()
        if line == "!!":
            if not self._history:
                raise ValueError("No previous command to repeat.")
            line = self._history[-1]
        elif line.startswith("!") and line[1:].isdigit():
            index = int(line[1:])
            if not 1 <= index <= len(self._history):
                raise ValueError(f"History entry {index} does not exist.")
            line = self._history[index - 1]
        if line:
            self._history.append(line)
        return self.parse_command(line)

    @staticmethod
    def resolve_command(name: str) -> str:
        """Resolve a command name or shortcut to its canonical name.

        Args:
            name: Raw command word.

        Returns:
            Canonical command name.

        Raises:
            ValueError: If the command is unknown.
        """
        name = name.lower()
        if name in ALIASES:
            return ALIASES[name]
        if name in COMMANDS:
            return name
        raise ValueError(f"Unknown command '{name}'. Type 'help' for the command list.")

    @classmethod
    def parse_command(cls, line: str) -> Tuple[str, List[str]]:
        """Split a line into a canonical command and its arguments.

        Args:
            line: Raw input line.

        Returns:
            ``(command, args)``.
        """
        parts = line.split()
        if not parts:
            return "", []
        return cls.resolve_command(parts[0]), parts[1:]

    @staticmethod
    def _to_coordinate(token: str, label: str) -> int:
        """Convert one token to a validated integer coordinate."""
        try:
            value = int(token)
        except (TypeError, ValueError):
            raise ValueError(f"{label} '{token}' is not an integer.") from None
        if not 0 <= value <= MAX_INPUT_COORD:
            raise ValueError(f"{label} {value} is out of range (0-{MAX_INPUT_COORD}).")
        return value

    def parse_coordinates(self, tokens: List[str]) -> List[int]:
        """Validate four coordinate tokens.

        Args:
            tokens: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            Four validated integers.

        Raises:
            ValueError: If the count, type or range is invalid.
        """
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y.")
        return [self._to_coordinate(tok, COORD_LABELS[i]) for i, tok in enumerate(tokens)]

    def prompt_coordinates(self) -> List[int]:
        """Interactively ask for the four coordinates.

        Returns:
            Four validated integers.

        Raises:
            ValueError: If the user types 'cancel'.
        """
        values: List[int] = []
        for label in COORD_LABELS:
            while True:
                raw = self._reader(f"  {label} (0-{MAX_INPUT_COORD}, or 'cancel'): ").strip()
                if raw.lower() == "cancel":
                    raise ValueError("Order entry cancelled.")
                try:
                    values.append(self._to_coordinate(raw, label))
                    break
                except ValueError as exc:
                    print(f"  {exc} Please try again.")
        return values
