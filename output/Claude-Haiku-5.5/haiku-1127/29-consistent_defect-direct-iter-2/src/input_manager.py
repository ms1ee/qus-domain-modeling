"""Command parsing, shortcut handling and input validation."""

import logging
from typing import List, Sequence, Tuple

logger = logging.getLogger(__name__)

COORD_MIN = 0
COORD_MAX = 1000

COMMANDS = ("start", "status", "orders", "riders", "map", "tick",
            "save", "help", "quit", "exit")

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "sv": "save",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
}

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] [s]  Create an order: restaurant (rx, ry) and customer
                           (cx, cy), coordinates 0-1000. Prompts if omitted.
  status [st]              Show system funds, riders and their orders.
  orders [o]               Show all orders with time, distance and rider.
  riders [r]               Show every rider status change log.
  map [m]                  Show the 16x16 ASCII map of riders and orders.
  tick [n] [t]             Advance the simulation by n ticks (default 1).
  save [path] [sv]         Save state to a JSON file (default dispatch_state.json).
  help [h, ?]              Show this help.
  quit [q] / exit [x]      Leave the program.
"""


class InputError(ValueError):
    """Raised when user input is malformed or out of range."""


class InputManager:
    """Parses user commands and validates coordinate input."""

    def __init__(self) -> None:
        """Create the input manager with an empty command history."""
        self.history: List[str] = []

    def parse_command(self, line: str) -> Tuple[str, List[str]]:
        """Split a raw input line into a canonical command and arguments.

        Args:
            line: Raw line typed by the user.

        Returns:
            Tuple ``(command, args)``. The command is an empty string for
            blank input and is resolved through shortcut aliases.
        """
        parts = line.strip().split()
        if not parts:
            return "", []
        cmd = parts[0].lower()
        cmd = ALIASES.get(cmd, cmd)
        return cmd, parts[1:]

    def validate_coordinates(self, tokens: Sequence[str]) -> List[int]:
        """Validate four integer coordinates in the range 0-1000.

        Args:
            tokens: Raw text tokens: restaurant x, y, customer x, y.

        Returns:
            List of four integers.

        Raises:
            InputError: If the count, type or range is invalid.
        """
        if len(tokens) != 4:
            raise InputError(
                "expected 4 integers: restaurant_x restaurant_y "
                "customer_x customer_y")
        values: List[int] = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise InputError(f"'{token}' is not an integer") from None
            if not COORD_MIN <= value <= COORD_MAX:
                raise InputError(
                    f"coordinate {value} out of range "
                    f"[{COORD_MIN}, {COORD_MAX}]")
            values.append(value)
        return values

    def parse_tick_count(self, args: Sequence[str]) -> int:
        """Parse the optional tick count argument for the tick command.

        Args:
            args: Command arguments.

        Returns:
            Number of ticks to run (1-10000).

        Raises:
            InputError: If the value is not an integer or out of range.
        """
        if not args:
            return 1
        try:
            steps = int(args[0])
        except ValueError:
            raise InputError(f"'{args[0]}' is not an integer") from None
        if not 1 <= steps <= 10000:
            raise InputError("tick count must be between 1 and 10000")
        return steps

    def record_history(self, line: str) -> None:
        """Remember a non-empty command line for history recall.

        Args:
            line: The command line to record.
        """
        if line.strip():
            self.history.append(line.strip())

    def setup_readline(self) -> None:
        """Enable arrow-key line editing and history when readline exists."""
        try:
            import readline  # noqa: F401  (side effect: enables editing)
        except ImportError:
            logger.debug("readline not available; history disabled")
