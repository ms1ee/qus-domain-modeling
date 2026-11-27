"""Command parsing, validation, shortcuts and command history."""

import logging

from config import CONFIG

logger = logging.getLogger("dispatch")

COORD_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")
MAX_TICKS_PER_COMMAND = 1000

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order (restaurant x y, customer x y; 0-800).
                       Prompts for the four values if omitted.
  status (st)          Show funds, riders, states and consistency.
  orders (o)           Show all orders.
  riders (r)           Show every recorded rider status change.
  map (m)              Show the ASCII map with riders and orders.
  tick [n] (t)         Advance the simulation by n ticks (default 1).
  history              Show command history.
  !!  /  !n           Repeat the last command / the n-th history entry.
  help (h, ?)          Show this help.
  quit (q) / exit (x)  Exit the program.
"""


class Command:
    """A parsed user command.

    Attributes:
        name: Canonical command name.
        arguments: Integer arguments (possibly empty).
    """

    def __init__(self, name, arguments=None):
        """Create a command.

        Args:
            name: Canonical command name.
            arguments: Optional list of integer arguments.
        """
        self.name = name
        self.arguments = list(arguments or [])


class InputManager:
    """Parses user input and maintains command history.

    Attributes:
        command_history: Previously entered command lines.
        history_size: Maximum number of stored history entries.
    """

    COMMANDS = ("start", "status", "orders", "riders", "map", "tick",
                "history", "help", "quit", "exit")
    SHORTCUTS = {
        "s": "start", "st": "status", "o": "orders", "r": "riders",
        "m": "map", "t": "tick", "h": "help", "?": "help",
        "q": "quit", "x": "exit",
    }

    def __init__(self, history_size=50):
        """Create an input manager.

        Args:
            history_size: Number of command lines to retain.
        """
        self.command_history = []
        self.history_size = max(1, int(history_size))

    @staticmethod
    def read_line(prompt="dispatch> "):
        """Read one raw line from standard input."""
        return input(prompt)

    @staticmethod
    def parse_integer(text, label):
        """Convert text to an integer with a descriptive error message.

        Raises:
            ValueError: If the text is not an integer.
        """
        try:
            return int(str(text).strip())
        except ValueError:
            raise ValueError(f"{label} must be an integer, got '{text}'") from None

    @staticmethod
    def validate_coordinate(value, label):
        """Check that a coordinate lies within 0..map_size.

        Raises:
            ValueError: If the coordinate is out of range.
        """
        limit = CONFIG["map_size"]
        if not 0 <= value <= limit:
            raise ValueError(f"{label} must be between 0 and {limit}, got {value}")
        return value

    def read_coordinates(self, read_fn):
        """Interactively prompt for the four order coordinates.

        Invalid entries are reported and the prompt is repeated.

        Args:
            read_fn: Callable accepting a prompt and returning a string.

        Returns:
            List of four validated integers.
        """
        values = []
        for label in COORD_LABELS:
            while True:
                raw = read_fn(f"{label} (0-{CONFIG['map_size']}): ")
                try:
                    value = self.parse_integer(raw, label)
                    self.validate_coordinate(value, label)
                except ValueError as exc:
                    print(f"Error: {exc}")
                    continue
                values.append(value)
                break
        return values

    def expand_history(self, line):
        """Resolve '!!' and '!n' history references.

        Raises:
            ValueError: If the referenced history entry does not exist.
        """
        stripped = line.strip()
        if stripped == "!!":
            if not self.command_history:
                raise ValueError("no previous command in history")
            return self.command_history[-1]
        if stripped.startswith("!") and stripped[1:].isdigit():
            index = int(stripped[1:])
            if not 1 <= index <= len(self.command_history):
                raise ValueError(f"history entry {index} does not exist")
            return self.command_history[index - 1]
        return line

    def record(self, line):
        """Store a successfully parsed command line in history."""
        self.command_history.append(line.strip())
        if len(self.command_history) > self.history_size:
            del self.command_history[0]

    def parse(self, line):
        """Parse and validate a command line.

        Args:
            line: Raw input text.

        Returns:
            A Command instance.

        Raises:
            ValueError: On empty input, unknown commands, wrong argument
                counts, non-integer values or out-of-range coordinates.
        """
        tokens = line.replace(",", " ").split()
        if not tokens:
            raise ValueError("empty command")
        raw_name = tokens[0].lower()
        name = self.SHORTCUTS.get(raw_name, raw_name)
        if name not in self.COMMANDS:
            raise ValueError(f"unknown command '{tokens[0]}'. Type 'help' for a list.")
        args = tokens[1:]

        if name == "start":
            if args and len(args) != 4:
                raise ValueError("start expects four integers: restaurant x y, customer x y")
            values = []
            for token, label in zip(args, COORD_LABELS):
                value = self.parse_integer(token, label)
                values.append(self.validate_coordinate(value, label))
            return Command(name, values)

        if name == "tick":
            if len(args) > 1:
                raise ValueError("tick accepts at most one argument")
            if not args:
                return Command(name, [1])
            steps = self.parse_integer(args[0], "tick count")
            if not 1 <= steps <= MAX_TICKS_PER_COMMAND:
                raise ValueError(f"tick count must be between 1 and {MAX_TICKS_PER_COMMAND}")
            return Command(name, [steps])

        if args:
            raise ValueError(f"'{name}' does not take arguments")
        return Command(name, [])
