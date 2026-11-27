"""Command parsing, input validation and command history."""

import logging

import config

try:  # Enables line editing and up/down history where available.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - not available on some platforms
    readline = None

logger = logging.getLogger("dispatch.input")

COMMAND_ALIASES = {
    "s": "start",
    "st": "start",
    "stat": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "hist": "history",
    "q": "quit",
    "x": "exit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order (restaurant then customer, 0-800).
                       Without arguments you will be prompted.
  status  (s)          Show system funds, riders, states and order lists.
  orders  (o)          Show details for all orders.
  riders  (r)          Show the status-change log of every rider.
  map     (m)          Show the ASCII map with riders and active orders.
  tick [n] (t)         Advance the simulation by n ticks (default 1).
  history (hist)       Show previously entered commands.
  help    (h, ?)       Show this help.
  quit    (q), exit    Save state and exit.
Shortcut: !! repeats the previous command.
"""


class InputManager:
    """Reads and validates user commands.

    Args:
        reader: Callable used to read a line (defaults to ``input``).
        writer: Callable used to print messages (defaults to ``print``).
    """

    def __init__(self, reader=input, writer=print):
        self._reader = reader
        self._writer = writer
        self._history = []

    def read_line(self, prompt="dispatch> "):
        """Read one raw line from the user.

        Args:
            prompt: Prompt text.

        Returns:
            str: The stripped input line.
        """
        return self._reader(prompt).strip()

    def read_command(self):
        """Read and parse the next command, honouring ``!!`` and history.

        Returns:
            tuple[str, list[str]]: Canonical command name and its arguments.
        """
        line = self.read_line()
        if line == "!!":
            if not self._history:
                self._writer("No previous command to repeat.")
                return "", []
            line = self._history[-1]
            self._writer(f"Repeating: {line}")
        if line:
            self._history.append(line)
        return self.parse_command(line)

    @staticmethod
    def parse_command(line):
        """Split a command line into a canonical name and arguments.

        Args:
            line: Raw command text.

        Returns:
            tuple[str, list[str]]: Command name (lower case) and arguments.
        """
        tokens = line.split()
        if not tokens:
            return "", []
        name = tokens[0].lower()
        return COMMAND_ALIASES.get(name, name), tokens[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Validate four integer coordinates.

        Args:
            tokens: Sequence of four values (strings or ints).

        Returns:
            list[int]: The validated integers.

        Raises:
            ValueError: If the count, type or range is wrong.
        """
        tokens = list(tokens)
        if len(tokens) != 4:
            raise ValueError(
                "expected four integers: restaurant_x restaurant_y customer_x customer_y "
                f"(got {len(tokens)})"
            )
        values = []
        for token in tokens:
            text = str(token).strip()
            try:
                value = int(text)
            except ValueError:
                raise ValueError(f"'{text}' is not an integer") from None
            if not config.COORD_MIN <= value <= config.COORD_MAX:
                raise ValueError(
                    f"coordinate {value} is outside the allowed range "
                    f"{config.COORD_MIN}-{config.COORD_MAX}"
                )
            values.append(value)
        return values

    def prompt_coordinates(self):
        """Prompt repeatedly until four valid coordinates are entered.

        Returns:
            list[int] | None: Coordinates, or None if the user cancels.
        """
        prompt = (
            "Enter restaurant_x restaurant_y customer_x customer_y "
            "(or 'cancel'): "
        )
        while True:
            line = self.read_line(prompt)
            if line.lower() in ("cancel", "c"):
                return None
            try:
                return self.parse_coordinates(line.replace(",", " ").split())
            except ValueError as exc:
                self._writer(f"Invalid input: {exc}")

    def history(self):
        """Return the previously entered command lines.

        Returns:
            list[str]: Copy of the command history.
        """
        return list(self._history)
