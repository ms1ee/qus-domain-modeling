"""Command parsing, validation and command history."""

from typing import Callable, List, Optional, Sequence, Tuple

from grid_map import MAP_SIZE

try:  # readline is optional and not available on every platform
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None  # type: ignore[assignment]

COMMANDS = (
    "start", "status", "orders", "riders", "map", "tick",
    "history", "help", "quit", "exit",
)
ALIASES = {
    "a": "start",
    "s": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "q": "quit",
    "hist": "history",
}
MAX_TICKS_PER_COMMAND = 1000

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] [a]  Create an order: restaurant then customer position
                           (0-800 integers). Prompts if no values given.
  status [s]               Show system funds, riders and their orders.
  orders [o]               Show all orders with timing and rider details.
  riders [r]               Show every rider status-change event.
  map [m]                  Show the ASCII map with riders, orders and routes.
  tick [n] [t]             Advance the simulation by n ticks (default 1).
  history [hist]           Show previously entered commands.
  !!                       Repeat the previous command.
  help [h, ?]              Show this help.
  quit [q] / exit          Save state (if enabled) and exit."""


class InputError(ValueError):
    """Raised for malformed or invalid user input."""


class InputManager:
    """Parses user commands, validates arguments and keeps history."""

    def __init__(self, history_limit: int = 200,
                 input_func: Callable[[str], str] = input) -> None:
        """Create the input manager.

        Args:
            history_limit: Maximum number of commands kept in history.
            input_func: Function used to read a line (replaceable for I/O).
        """
        self.command_history: List[str] = []
        self._history_limit = history_limit
        self._input = input_func
        self._setup_readline()

    def _setup_readline(self) -> None:
        """Enable arrow-key history when readline is available."""
        if readline is None:
            return
        try:
            readline.set_history_length(self._history_limit)
        except Exception:  # noqa: BLE001 - optional feature
            pass

    def record(self, line: str) -> None:
        """Add a command to the history, trimming old entries.

        Args:
            line: Command text.
        """
        self.command_history.append(line)
        overflow = len(self.command_history) - self._history_limit
        if overflow > 0:
            del self.command_history[:overflow]

    def expand_history(self, raw: str) -> str:
        """Expand history shortcuts such as '!!' and '!3'.

        Args:
            raw: Raw input line.

        Returns:
            The expanded command text.

        Raises:
            InputError: If the referenced history entry does not exist.
        """
        if raw == "!!":
            if not self.command_history:
                raise InputError("no previous command in history.")
            return self.command_history[-1]
        if raw.startswith("!") and raw[1:].isdigit():
            index = int(raw[1:])
            if not 1 <= index <= len(self.command_history):
                raise InputError(f"history entry {index} does not exist.")
            return self.command_history[index - 1]
        return raw

    def read_command(self, prompt: str = "dispatch> ") -> str:
        """Read, expand and record one command line.

        Args:
            prompt: Prompt text shown to the user.

        Returns:
            The command line (may be empty).

        Raises:
            EOFError: If input is closed.
            InputError: If a history shortcut cannot be expanded.
        """
        raw = self._input(prompt).strip()
        line = self.expand_history(raw)
        if line:
            self.record(line)
        return line

    def parse(self, line: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command name and arguments.

        Args:
            line: Command text.

        Returns:
            Tuple of (command name, argument tokens).

        Raises:
            InputError: If the command is empty or unknown.
        """
        tokens = line.replace(",", " ").split()
        if not tokens:
            raise InputError("empty command. Type 'help' for the command list.")
        name = tokens[0].lower()
        name = ALIASES.get(name, name)
        if name not in COMMANDS:
            raise InputError(
                f"unknown command '{tokens[0]}'. Type 'help' for the command list."
            )
        return name, tokens[1:]

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Validate four integer coordinates.

        Args:
            tokens: Exactly four tokens: restaurant x and y, customer x and y.

        Returns:
            The four integers.

        Raises:
            InputError: If the count, type or range is invalid.
        """
        if len(tokens) != 4:
            raise InputError(
                "expected 4 integers: restaurant_x restaurant_y customer_x customer_y"
            )
        values: List[int] = []
        for token in tokens:
            try:
                value = int(token)
            except (TypeError, ValueError):
                raise InputError(f"'{token}' is not an integer.") from None
            if not 0 <= value <= MAP_SIZE:
                raise InputError(
                    f"coordinate {value} is out of range 0-{MAP_SIZE}."
                )
            values.append(value)
        return values

    def prompt_coordinates(self) -> List[int]:
        """Interactively ask for the four coordinates.

        Returns:
            The four validated integers.

        Raises:
            InputError: If any value is invalid.
        """
        labels = ("restaurant x", "restaurant y", "customer x", "customer y")
        tokens = [self._input(f"  {label} (0-{MAP_SIZE}): ").strip() for label in labels]
        return self.parse_coordinates(tokens)

    @staticmethod
    def parse_tick_count(tokens: Sequence[str]) -> int:
        """Parse the optional tick count argument of the tick command.

        Args:
            tokens: Argument tokens.

        Returns:
            Number of ticks to run (default 1).

        Raises:
            InputError: If the value is not a positive integer within limits.
        """
        if not tokens:
            return 1
        try:
            count = int(tokens[0])
        except ValueError:
            raise InputError(f"'{tokens[0]}' is not an integer.") from None
        if not 1 <= count <= MAX_TICKS_PER_COMMAND:
            raise InputError(
                f"tick count must be between 1 and {MAX_TICKS_PER_COMMAND}."
            )
        return count
