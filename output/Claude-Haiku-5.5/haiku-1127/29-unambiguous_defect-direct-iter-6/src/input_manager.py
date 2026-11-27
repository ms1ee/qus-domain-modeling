"""Command parsing, input validation, and command history."""

import logging

import config

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
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
    "history": "history",
    "hist": "history",
    "save": "save",
    "help": "help",
    "h": "help",
    "?": "help",
    "quit": "quit",
    "exit": "quit",
    "q": "quit",
}


class InputError(ValueError):
    """Raised when user-supplied values are malformed or out of range."""


class CommandError(ValueError):
    """Raised when a command name is not recognised."""


class InputManager:
    """Read, parse, and validate user commands."""

    def __init__(self):
        """Create the manager and enable line editing when available."""
        self.history = []
        self._line_editing = self._enable_line_editing()

    @staticmethod
    def _enable_line_editing():
        """Import readline so arrow keys recall previous input.

        Returns:
            True if readline is available, otherwise False.
        """
        try:
            import readline  # noqa: F401
        except ImportError:
            logger.debug("readline unavailable; line editing disabled")
            return False
        return True

    @property
    def line_editing(self):
        """Return True when readline-based history recall is active."""
        return self._line_editing

    def read_line(self, prompt="dispatch> "):
        """Read one line from standard input.

        Args:
            prompt: Prompt text.

        Returns:
            The stripped input line (possibly empty).

        Raises:
            EOFError: If input is closed.
        """
        line = input(prompt).strip()
        if line:
            self.history.append(line)
        return line

    @staticmethod
    def parse_command(line):
        """Split a command line into a canonical command name and arguments.

        Args:
            line: Raw input line.

        Returns:
            Tuple ``(command_name, args)``. The name is empty for blank input.

        Raises:
            CommandError: If the command is unknown.
        """
        parts = line.replace(",", " ").split()
        if not parts:
            return "", []
        name = COMMAND_ALIASES.get(parts[0].lower())
        if name is None:
            raise CommandError(f"unknown command '{parts[0]}'; type 'help' for a list")
        return name, parts[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Validate four integer coordinates.

        Args:
            tokens: Sequence of four string tokens.

        Returns:
            List of four integers.

        Raises:
            InputError: If the count, type, or range is invalid.
        """
        tokens = list(tokens)
        if len(tokens) != 4:
            raise InputError(
                "expected 4 integers: restaurant_x restaurant_y customer_x customer_y"
            )
        values = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise InputError(f"'{token}' is not an integer") from None
            if not config.COORD_MIN <= value <= config.COORD_MAX:
                raise InputError(
                    f"coordinate {value} is outside the range "
                    f"{config.COORD_MIN}-{config.COORD_MAX}"
                )
            values.append(value)
        return values

    def prompt_coordinates(self):
        """Ask the user for four coordinates interactively.

        Returns:
            List of four validated integers.

        Raises:
            InputError: If the entered values are invalid.
        """
        line = self.read_line(
            "Enter restaurant_x restaurant_y customer_x customer_y: "
        )
        return self.parse_coordinates(line.replace(",", " ").split())

    def history_lines(self, limit=20):
        """Return the most recent commands as numbered text lines.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            Multi-line string.
        """
        if not self.history:
            return "No command history yet."
        start = max(len(self.history) - limit, 0)
        return "\n".join(
            f"{index + 1:>4}  {entry}"
            for index, entry in enumerate(self.history[start:], start=start)
        )

    @staticmethod
    def help_text():
        """Return the list of available commands.

        Returns:
            Multi-line help string.
        """
        return "\n".join([
            "Commands (each command advances simulated time by one tick):",
            "  start [rx ry cx cy]  create an order (restaurant then customer, 0-800)",
            "  status (st)          funds, riders, states, and order lists",
            "  orders (o)           details of all orders",
            "  riders (r)           event log of every rider",
            "  map (m)              ASCII map of riders and active orders",
            "  tick [n]             advance simulated time by n ticks (1-1000)",
            "  save [file]          save state to a JSON file",
            "  history (hist)       recent command history",
            "  help (h, ?)          show this list",
            "  quit (q, exit)       leave the simulator",
            "Shortcuts: arrow keys recall history when readline is available.",
        ])
