"""Command parsing, shortcut expansion and input validation."""

from typing import Callable, List, Sequence, Tuple

from path_planner import GRID_SIZE


class CommandError(ValueError):
    """Raised when user input cannot be understood or is invalid."""


COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick", "next": "tick", "n": "tick",
    "history": "history", "h": "history",
    "save": "save",
    "help": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order. Restaurant (rx,ry) and customer (cx,cy)
                       are integers 0-800. Prompts for them when omitted.
  status (st)          Show funds, time, and every rider's state and orders.
  orders (o)           Show all orders with time, distance, rider and status.
  riders (r)           Show every rider's status-change history.
  map (m)              Show the ASCII map with riders and active orders.
  tick [n] (t, n)      Advance simulated time by n ticks (default 1).
                       Pressing Enter on an empty line also advances one tick.
  history (h)          Show the command history.
  save [file]          Save a JSON snapshot (default state.json).
  help (?)             Show this help.
  quit (q, exit)       Leave the simulator.
Shortcuts: !! repeats the last command, !N repeats history entry N.
"""


class InputManager:
    """Reads, expands and parses user commands."""

    MAX_TICKS_PER_COMMAND = 1000

    def __init__(self, reader: Callable[[str], str] = input) -> None:
        """Create the manager.

        Args:
            reader: Function used to read a line (injectable for testing).
        """
        self._reader = reader
        self.history: List[str] = []

    def read_line(self, prompt: str) -> str:
        """Read one line from the user and store it in the history.

        Args:
            prompt: Prompt text.

        Returns:
            The stripped input line.
        """
        line = self._reader(prompt).strip()
        if line and not line.startswith("!"):
            self.history.append(line)
        return line

    def resolve(self, line: str) -> Tuple[str, List[str]]:
        """Expand shortcuts and split a line into (command, arguments).

        Args:
            line: Raw user input.

        Returns:
            Tuple of canonical command name and argument tokens. An empty
            line maps to advancing one tick.

        Raises:
            CommandError: If the command is unknown or a history reference is invalid.
        """
        stripped = line.strip()
        if not stripped:
            return "tick", []
        if stripped.startswith("!"):
            stripped = self._expand_history(stripped)
        tokens = stripped.replace(",", " ").split()
        command = COMMAND_ALIASES.get(tokens[0].lower())
        if command is None:
            raise CommandError(
                f"Unknown command '{tokens[0]}'. Type 'help' for the command list.")
        return command, tokens[1:]

    def _expand_history(self, text: str) -> str:
        """Resolve '!!' or '!N' into a previously entered command."""
        if not self.history:
            raise CommandError("No command history yet.")
        spec = text[1:].strip()
        if spec in ("", "!"):
            return self.history[-1]
        if spec.isdigit():
            index = int(spec)
            if 1 <= index <= len(self.history):
                return self.history[index - 1]
            raise CommandError(f"No history entry {index}.")
        raise CommandError("Invalid history reference. Use !! or !N.")

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Parse and validate four integer coordinates.

        Args:
            tokens: Tokens such as ["100", "200", "300", "400"]; commas are
                accepted as separators.

        Returns:
            [restaurant_x, restaurant_y, customer_x, customer_y].

        Raises:
            CommandError: On wrong count, non-integer or out-of-range values.
        """
        values = " ".join(tokens).replace(",", " ").split()
        if len(values) != 4:
            raise CommandError(
                "Expected 4 integers: restaurant_x restaurant_y customer_x customer_y")
        result = []
        for token in values:
            try:
                value = int(token)
            except ValueError as exc:
                raise CommandError(f"'{token}' is not an integer coordinate") from exc
            if not 0 <= value <= GRID_SIZE:
                raise CommandError(
                    f"Coordinate {value} is out of range 0-{GRID_SIZE}")
            result.append(value)
        return result

    @classmethod
    def parse_tick_count(cls, args: Sequence[str]) -> int:
        """Parse the optional tick count argument of the 'tick' command.

        Args:
            args: Argument tokens (zero or one integer).

        Returns:
            Number of ticks to simulate (1 if omitted).

        Raises:
            CommandError: If the argument is not an integer in range.
        """
        if not args:
            return 1
        if len(args) > 1:
            raise CommandError("tick takes at most one argument")
        try:
            steps = int(args[0])
        except ValueError as exc:
            raise CommandError(f"'{args[0]}' is not an integer tick count") from exc
        if not 1 <= steps <= cls.MAX_TICKS_PER_COMMAND:
            raise CommandError(
                f"Tick count must be between 1 and {cls.MAX_TICKS_PER_COMMAND}")
        return steps
