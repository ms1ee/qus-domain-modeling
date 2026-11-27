"""Command parsing, shortcut handling, history and input validation."""

import logging

from grid import MAP_SIZE, validate_coordinate

try:  # enables arrow-key line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows without pyreadline
    readline = None

logger = logging.getLogger("dispatch.input")

COMMAND_NAMES = ("start", "status", "orders", "riders", "wait", "history",
                 "save", "help", "quit", "exit")

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "t": "wait",
    "hist": "history",
    "w": "save",
    "h": "help",
    "?": "help",
    "q": "quit",
    "e": "exit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  (s)  Create an order: restaurant then customer
                            coordinates (0-800). Prompts if omitted.
  status               (st) Show system funds, riders and map.
  orders               (o)  Show all orders.
  riders               (r)  Show every rider status-change record.
  wait [n]             (t)  Advance simulated time by n ticks (default 1).
  history              (hist) Show command history.
  save [path]          (w)  Save a JSON snapshot of the system state.
  help                 (h)  Show this help.
  quit / exit          (q)  Leave the program.
  !!  repeat last command, !n repeat history entry n.
"""


class InputManager:
    """Reads, expands and parses user commands and coordinates."""

    def __init__(self, reader=None) -> None:
        """Create an input manager.

        Args:
            reader: Callable used to read a line (defaults to ``input``).
        """
        self._reader = reader or input
        self.history = []

    def read_line(self, prompt: str = "> ") -> str:
        """Read one raw line from the user."""
        return self._reader(prompt)

    def read_command(self, prompt: str = "> "):
        """Read a command line, expanding history shortcuts.

        Returns:
            The command string, or None for an empty line.

        Raises:
            ValueError: If a history shortcut cannot be resolved.
        """
        raw = self.read_line(prompt).strip()
        if not raw:
            return None
        if raw == "!!":
            if not self.history:
                raise ValueError("No previous command to repeat.")
            raw = self.history[-1]
        elif raw.startswith("!") and raw[1:].isdigit():
            index = int(raw[1:]) - 1
            if index < 0 or index >= len(self.history):
                raise ValueError(f"No history entry {raw[1:]}.")
            raw = self.history[index]
        self.history.append(raw)
        return raw

    @staticmethod
    def parse_command(line: str) -> tuple:
        """Split a command line into a canonical command and its arguments.

        Args:
            line: Raw command text.

        Returns:
            Tuple (command_name, argument_list).
        """
        parts = line.split()
        if not parts:
            return "", []
        name = parts[0].lower()
        return ALIASES.get(name, name), parts[1:]

    @staticmethod
    def validate_coordinates(values) -> list:
        """Validate that every value is an integer in the range 0-800.

        Args:
            values: Iterable of raw values.

        Returns:
            List of validated ints.

        Raises:
            ValueError: On the first invalid value.
        """
        return [validate_coordinate(v) for v in values]

    def parse_coordinates(self, tokens) -> list:
        """Parse four command-line tokens into validated coordinates.

        Raises:
            ValueError: If the count is wrong, a token is not an integer, or
                a value is outside 0-800.
        """
        if len(tokens) != 4:
            raise ValueError("expected 4 integer coordinates: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for token in tokens:
            try:
                values.append(int(token))
            except ValueError:
                raise ValueError(f"'{token}' is not an integer") from None
        return self.validate_coordinates(values)

    def prompt_coordinates(self):
        """Interactively ask for the four coordinates, re-prompting on errors.

        Returns:
            List of four validated ints, or None if the user cancelled by
            entering an empty line.
        """
        labels = ["Restaurant X", "Restaurant Y", "Customer X", "Customer Y"]
        values = []
        for label in labels:
            while True:
                raw = self.read_line(f"{label} (0-{MAP_SIZE}, blank to "
                                     "cancel): ").strip()
                if raw == "":
                    return None
                try:
                    values.append(self.parse_coordinates([raw])[0])
                    break
                except ValueError as exc:
                    print(f"Invalid value: {exc}. Please try again.")
        return values
