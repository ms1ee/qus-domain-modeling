"""Command parsing, shortcut resolution, history and input validation."""

import logging
import re

from path_planner import validate_coordinate

try:  # Enables line editing and up/down history where readline exists.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "start": "start", "s": "start", "order": "start",
    "status": "status", "st": "status",
    "orders": "orders", "od": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "run": "run", "go": "run",
    "history": "history", "h": "history",
    "help": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}

COORDINATE_NAMES = ["restaurant x", "restaurant y",
                    "customer x", "customer y"]

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] [s]  Enter restaurant and customer coordinates (0-800)
  status [st]              Funds, riders, their states and order lists
  orders [od]              Details of all orders
  riders [r]               Status-change log of every rider
  map [m]                  ASCII map with riders and active orders
  tick [n] [t]             Advance simulated time by n ticks (default 1)
  run [go]                 Advance until all active orders are delivered
  history [h]              Show command history
  !! / !n                  Repeat the last command / history entry n
  help [?]                 Show this help
  quit [q] / exit          Leave the program"""


class InputManager:
    """Reads, validates and parses user commands."""

    def __init__(self):
        """Create an input manager with an empty command history."""
        self.history = []

    def read_line(self, prompt):
        """Read one line from standard input.

        Args:
            prompt: Prompt text.

        Returns:
            The entered line, or "quit" on end-of-file or Ctrl-C.
        """
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"

    def record(self, line):
        """Append an executed command to the history."""
        self.history.append(line)

    def resolve(self, line):
        """Expand history references ('!!' and '!n') in ``line``.

        Args:
            line: Raw user input.

        Returns:
            The command text to execute.

        Raises:
            ValueError: If the referenced history entry does not exist.
        """
        text = line.strip()
        if text == "!!":
            if not self.history:
                raise ValueError("no commands in history to repeat")
            return self.history[-1]
        if text.startswith("!") and text[1:].isdigit():
            index = int(text[1:])
            if not 1 <= index <= len(self.history):
                raise ValueError(f"history entry {index} does not exist")
            return self.history[index - 1]
        return text

    @staticmethod
    def parse(line):
        """Split a command line into a canonical command name and arguments.

        Args:
            line: Command text.

        Returns:
            Tuple ``(command, args)``. ``command`` is None when unknown or
            when the line is empty.
        """
        tokens = line.split()
        if not tokens:
            return None, []
        return COMMAND_ALIASES.get(tokens[0].lower()), tokens[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Parse four integer coordinates in the range 0-800.

        Accepts separate tokens or a single string with spaces or commas.

        Args:
            tokens: List of tokens, or a string.

        Returns:
            List of four validated integers
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the count is wrong, a value is not an integer,
                or a value is outside 0-800.
        """
        if isinstance(tokens, str):
            text = tokens
        else:
            text = " ".join(tokens)
        parts = [p for p in re.split(r"[\s,]+", text.strip()) if p]
        if len(parts) != 4:
            raise ValueError("expected four integers: restaurant_x "
                             "restaurant_y customer_x customer_y")
        values = []
        for part, name in zip(parts, COORDINATE_NAMES):
            try:
                number = int(part)
            except ValueError:
                raise ValueError(f"{name} must be an integer, got '{part}'")
            values.append(validate_coordinate(number, name))
        return values

    @staticmethod
    def parse_count(tokens, default=1, maximum=1000):
        """Parse an optional positive tick count.

        Args:
            tokens: Argument list (may be empty).
            default: Value used when no argument is given.
            maximum: Largest allowed value.

        Returns:
            Integer count between 1 and ``maximum``.

        Raises:
            ValueError: If the argument is not a valid count.
        """
        if not tokens:
            return default
        try:
            count = int(tokens[0])
        except ValueError:
            raise ValueError(f"tick count must be an integer, got "
                             f"'{tokens[0]}'")
        if not 1 <= count <= maximum:
            raise ValueError(f"tick count must be between 1 and {maximum}")
        return count
