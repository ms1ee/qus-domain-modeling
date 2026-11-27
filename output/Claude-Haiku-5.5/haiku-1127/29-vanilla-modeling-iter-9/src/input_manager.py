"""Command parsing, input validation and command history.

Shortcut keys are supported (for example ``s`` for ``start``) and ``!!``
repeats the previous command.  When the standard ``readline`` module is
available, arrow keys also navigate the history on Unix-like systems.
"""

import logging

import grid

try:  # pragma: no cover - availability depends on platform
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "s": "start",
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
    "save": "save",
    "h": "help",
    "help": "help",
    "?": "help",
    "q": "quit",
    "quit": "quit",
    "exit": "quit",
}

HELP_TEXT = """Commands:
  start rx ry cx cy   Place an order (restaurant x,y then customer x,y; 0-800).
                      The simulation runs until the order is delivered.
  status (s, st)      Show system funds, riders, their positions, states and orders
  orders (o)          Show details of all orders
  riders (r)          Show every recorded status change of every rider
  map (m)             Show the 8x8 ASCII map with riders and orders
  tick [n] (t)        Advance the simulation by n ticks (default 1)
  save [file]         Save parameters, riders and orders to a JSON file
  help (h, ?)         Show this help
  quit (q, exit)      Exit the program
  !!                  Repeat the previous command
Coordinates may be separated by spaces or commas."""


class InputManager:
    """Reads, parses and validates user commands.

    Attributes:
        command_history (list[str]): every non-empty command entered.
    """

    def __init__(self, input_func=input):
        """Create an input manager.

        Args:
            input_func (callable): function used to read a line of input.
        """
        self.command_history = []
        self._input = input_func

    def read_command(self, prompt="food> "):
        """Read one command line, expanding ``!!`` to the previous command.

        Args:
            prompt (str): prompt shown to the user.

        Returns:
            str: the command text (may be empty).

        Raises:
            ValueError: if ``!!`` is used with an empty history.
        """
        raw = self._input(prompt).strip()
        if raw == "!!":
            if not self.command_history:
                raise ValueError("no previous command to repeat")
            raw = self.command_history[-1]
        if raw:
            self.command_history.append(raw)
        return raw

    def parse(self, line):
        """Split a command line into a canonical command name and arguments.

        Args:
            line (str): raw command text.

        Returns:
            tuple[str | None, list[str]]: command name (None for blank input)
            and the argument tokens.
        """
        tokens = line.replace(",", " ").split()
        if not tokens:
            return None, []
        name = tokens[0].lower()
        return COMMAND_ALIASES.get(name, name), tokens[1:]

    @staticmethod
    def parse_int(text, label="value"):
        """Convert a token to an integer with a friendly error message.

        Args:
            text (str): token to convert.
            label (str): description used in error messages.

        Returns:
            int: the parsed integer.

        Raises:
            ValueError: if the token is not an integer.
        """
        try:
            return int(text)
        except (TypeError, ValueError):
            raise ValueError(f"{label} must be an integer, got '{text}'") from None

    def parse_coordinates(self, args):
        """Parse and validate the four coordinates of a ``start`` command.

        Args:
            args (list[str]): tokens ``rx ry cx cy``.

        Returns:
            list[int]: validated coordinates.

        Raises:
            ValueError: on wrong count, non-integer or out-of-range values.
        """
        if len(args) != 4:
            raise ValueError(
                "start needs 4 integers: restaurant_x restaurant_y customer_x customer_y "
                "(example: start 100 200 700 600)"
            )
        values = [self.parse_int(token, "coordinate") for token in args]
        for value in values:
            grid.validate_coord(value, "coordinate")
        return values

    def parse_count(self, args, maximum=10000):
        """Parse an optional positive tick count.

        Args:
            args (list[str]): optional argument list; default count is 1.
            maximum (int): upper bound on the count.

        Returns:
            int: the tick count.

        Raises:
            ValueError: if the count is invalid.
        """
        if not args:
            return 1
        count = self.parse_int(args[0], "tick count")
        if not 1 <= count <= maximum:
            raise ValueError(f"tick count must be between 1 and {maximum}")
        return count
