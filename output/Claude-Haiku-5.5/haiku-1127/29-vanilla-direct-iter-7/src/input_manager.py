"""Command parsing, input validation and command history."""

import logging
import re

from constants import MAP_SIZE

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "run": "run",
    "h": "help",
    "?": "help",
    "hist": "history",
    "q": "quit",
    "x": "exit",
}

COMMAND_HELP = {
    "start": "start [rx ry cx cy]  Create an order (restaurant then customer coordinates, 0-800)",
    "status": "status              Show funds, riders and their current state",
    "orders": "orders              Show all orders with timing and assignment",
    "riders": "riders              Show every recorded rider status change",
    "map": "map                 Show the ASCII map (R rider, S restaurant, C customer)",
    "tick": "tick [n]             Advance the simulation by n ticks (default 1)",
    "run": "run                 Advance until all active orders are delivered",
    "history": "history             Show recent commands",
    "help": "help                Show this help",
    "quit": "quit / exit         Exit the program",
}


class InputManager:
    """Reads, parses and validates user commands.

    Args:
        reader: Callable used to read a line (default: built-in input).
        output: Callable used to print messages (default: built-in print).
        history_limit: Maximum number of commands kept in history.
    """

    def __init__(self, reader=input, output=print, history_limit=100):
        self._reader = reader
        self._output = output
        self.history = []
        self.history_limit = history_limit
        self._setup_readline()

    @staticmethod
    def _setup_readline():
        """Enable line editing and arrow-key history when readline is available."""
        try:
            import readline  # noqa: F401  (side effect: enables editing)
        except ImportError:
            logger.debug("readline not available; line editing disabled")

    def read_line(self, prompt):
        """Read a raw line from the user and strip surrounding whitespace.

        Raises:
            EOFError: When input is closed.
        """
        return self._reader(prompt).strip()

    def _remember(self, line):
        """Add a command to the history, respecting the size limit."""
        self.history.append(line)
        if len(self.history) > self.history_limit:
            del self.history[0]

    @staticmethod
    def parse_command(line):
        """Split a command line into a canonical command name and arguments.

        Args:
            line: Raw command text.

        Returns:
            tuple[str, list[str]]: Command name (lower case) and arguments.
        """
        parts = line.split()
        if not parts:
            return "", []
        word = parts[0].lower()
        return COMMAND_ALIASES.get(word, word), parts[1:]

    def read_command(self, prompt="dispatch> "):
        """Read and parse one command, supporting the '!!' repeat shortcut.

        Returns:
            tuple[str, list[str]]: Canonical command and its arguments. An
            empty command name is returned for blank input.

        Raises:
            EOFError: When input is closed.
        """
        line = self.read_line(prompt)
        if line == "!!":
            if not self.history:
                self._output("No previous command to repeat.")
                return "", []
            line = self.history[-1]
            self._output(f"Repeating: {line}")
        if line:
            self._remember(line)
        return self.parse_command(line)

    @staticmethod
    def parse_coordinates(value):
        """Parse four integer coordinates from text or a token list.

        Args:
            value: A string such as "100 200 300 400" or "100,200,300,400",
                or a sequence of tokens.

        Returns:
            list[int]: Four coordinates in the range 0..MAP_SIZE.

        Raises:
            ValueError: If the count, type or range is invalid.
        """
        if isinstance(value, str):
            tokens = [t for t in re.split(r"[\s,]+", value.strip()) if t]
        else:
            tokens = [str(t) for t in value]
        if len(tokens) != 4:
            raise ValueError(
                f"expected 4 integer coordinates (restaurant x y, customer x y), got {len(tokens)}"
            )
        coords = []
        for token in tokens:
            try:
                number = int(token)
            except ValueError:
                raise ValueError(f"'{token}' is not an integer")
            if not 0 <= number <= MAP_SIZE:
                raise ValueError(f"coordinate {number} is out of range 0-{MAP_SIZE}")
            coords.append(number)
        return coords

    def prompt_coordinates(self, max_attempts=3):
        """Interactively ask for four coordinates with retry on invalid input.

        Args:
            max_attempts: Number of invalid entries allowed before giving up.

        Returns:
            list[int] | None: Valid coordinates, or None if the user cancelled
            (blank line) or exhausted attempts.
        """
        for attempt in range(max_attempts):
            text = self.read_line(
                "Enter restaurant x y and customer x y (0-800), blank to cancel: "
            )
            if not text:
                self._output("Order cancelled.")
                return None
            try:
                return self.parse_coordinates(text)
            except ValueError as exc:
                remaining = max_attempts - attempt - 1
                self._output(f"Invalid input: {exc}.")
                if remaining:
                    self._output(f"Please try again ({remaining} attempt(s) left).")
        self._output("Too many invalid attempts; order cancelled.")
        return None

    def help_text(self):
        """Return the help text listing all commands."""
        lines = ["Available commands:"]
        lines.extend(f"  {COMMAND_HELP[name]}" for name in COMMAND_HELP)
        lines.append("Shortcuts: s=start st=status o=orders r=riders m=map t=tick "
                     "h=help q=quit, '!!' repeats the last command.")
        return "\n".join(lines)

    def history_text(self):
        """Return the numbered command history."""
        if not self.history:
            return "History is empty."
        return "\n".join(f"{i:>3}: {cmd}" for i, cmd in enumerate(self.history, 1))
