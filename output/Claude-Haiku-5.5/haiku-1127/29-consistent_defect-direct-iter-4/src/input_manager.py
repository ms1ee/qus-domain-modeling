"""Command parsing, input validation, shortcuts and command history."""

import logging

logger = logging.getLogger(__name__)

try:  # readline is optional (not always available on Windows)
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

PROMPT = "dispatch> "
COORD_MIN = 0
COORD_MAX = 1000

SHORTCUTS = {
    "n": "start",
    "s": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "w": "save",
    "l": "load",
    "y": "history",
    "h": "help",
    "?": "help",
    "q": "quit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Dispatch an order (restaurant x y, customer x y)
  status               Show system funds, riders and their order lists
  orders               Show all orders (time, locations, distance, rider)
  riders               Show every rider status change log
  map                  Show the 16x16 ASCII map
  tick [n]             Advance simulated time by n ticks (default 1)
  save [file]          Save state to JSON (default dispatch_state.json)
  load [file]          Load state from JSON
  history              Show recent commands
  help                 Show this help
  quit / exit          Leave the program
Shortcuts: n=start s=status o=orders r=riders m=map t=tick w=save
           l=load y=history h/?=help q=quit
Coordinates must be integers in 0-1000."""


class InputManager:
    """Reads and validates user commands.

    Args:
        input_func: Callable used to read a line (defaults to ``input``).
    """

    def __init__(self, input_func=input):
        """Create the input manager.

        Args:
            input_func: Callable returning one line of user input.
        """
        self._input = input_func
        self._history = []

    @property
    def history(self):
        """Return the list of entered command lines."""
        return list(self._history)

    def read_command(self):
        """Prompt for a command line and parse it.

        Returns:
            tuple[str, list[str]]: ``(command, arguments)``.
        """
        line = self._input(PROMPT)
        if line and line.strip():
            self._history.append(line.strip())
            if readline is not None:
                try:
                    readline.add_history(line.strip())
                except Exception:  # pragma: no cover - best effort only
                    logger.debug("readline history unavailable")
        return self.parse_command(line)

    @staticmethod
    def parse_command(line):
        """Split a raw line into a normalised command and its arguments.

        Args:
            line: Raw input text.

        Returns:
            tuple[str, list[str]]: Command name (lower case, shortcuts
            expanded) and argument tokens.
        """
        parts = (line or "").strip().split()
        if not parts:
            return "", []
        head = parts[0].lower()
        if len(head) == 1 and head in SHORTCUTS:
            head = SHORTCUTS[head]
        return head, parts[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Validate four integer coordinates.

        Args:
            tokens: Argument tokens; commas are treated as separators.

        Returns:
            list[int]: ``[restaurant_x, restaurant_y, customer_x,
            customer_y]``.

        Raises:
            ValueError: If the count, type or range is wrong.
        """
        items = " ".join(tokens).replace(",", " ").split()
        if len(items) != 4:
            raise ValueError("expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y")
        values = []
        for item in items:
            try:
                value = int(item)
            except ValueError:
                raise ValueError(f"'{item}' is not an integer")
            if not COORD_MIN <= value <= COORD_MAX:
                raise ValueError(f"coordinate {value} is out of range "
                                 f"{COORD_MIN}-{COORD_MAX}")
            values.append(value)
        return values

    def prompt_coordinates(self):
        """Interactively ask for the four order coordinates.

        Returns:
            list[int]: Validated coordinates.

        Raises:
            ValueError: If the input is invalid.
        """
        text = self._input("Enter restaurant_x restaurant_y customer_x "
                           "customer_y: ")
        return self.parse_coordinates(text.split())

    @staticmethod
    def help_text():
        """Return the help text for all commands."""
        return HELP_TEXT
