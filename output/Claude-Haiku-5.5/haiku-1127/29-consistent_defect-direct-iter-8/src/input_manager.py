"""Command parsing, coordinate validation and input history."""

from __future__ import annotations

import logging
import re
from typing import Callable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

COORD_MIN = 0
COORD_MAX = 1000
MAX_HISTORY = 100

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
    "save": "save",
    "w": "save",
    "history": "history",
    "h": "history",
    "help": "help",
    "?": "help",
    "quit": "quit",
    "exit": "quit",
    "q": "quit",
}

_SPLIT_PATTERN = re.compile(r"[\s,]+")


class InputManager:
    """Reads, records and parses user commands and coordinates."""

    def __init__(self, reader: Callable[[str], str] = input) -> None:
        """Create the manager.

        Args:
            reader: Callable used to read a line (defaults to ``input``).
        """
        self._reader = reader
        self.history: List[str] = []
        self._setup_readline()

    @staticmethod
    def _setup_readline() -> None:
        """Enable line editing and arrow-key history when available."""
        try:
            import readline  # noqa: F401  (side effect: enables editing)

            readline.set_history_length(MAX_HISTORY)
        except ImportError:
            logger.debug("readline not available; line editing disabled")

    def read_line(self, prompt: str) -> Optional[str]:
        """Read one line from the user.

        Args:
            prompt: Prompt text.

        Returns:
            The raw line, ``"quit"`` on Ctrl+C, or None on end of input.
        """
        try:
            return self._reader(prompt)
        except EOFError:
            return None
        except KeyboardInterrupt:
            print()
            return "quit"

    def record(self, line: str) -> None:
        """Append a non-empty command to the history."""
        if line.strip():
            self.history.append(line.strip())
            if len(self.history) > MAX_HISTORY:
                del self.history[0]

    def last_command(self) -> Optional[str]:
        """Return the most recent command in the history."""
        return self.history[-1] if self.history else None

    def resolve(self, line: str) -> Tuple[str, List[str]]:
        """Split a line into a canonical command name and its arguments.

        Args:
            line: Raw input line.

        Returns:
            Tuple ``(command, args)``. Unknown commands return ``"unknown"``.
        """
        tokens = line.strip().split()
        if not tokens:
            return "", []
        name = COMMAND_ALIASES.get(tokens[0].lower())
        if name is None:
            return "unknown", tokens
        return name, tokens[1:]

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Parse four integer coordinates from tokens.

        Accepts space- or comma-separated values.

        Args:
            tokens: Argument tokens.

        Returns:
            List of four integers.

        Raises:
            ValueError: If the count is wrong or a value is not an integer.
        """
        text = " ".join(tokens).strip()
        parts = [part for part in _SPLIT_PATTERN.split(text) if part]
        if len(parts) != 4:
            raise ValueError(
                "expected 4 coordinates: restaurant_x restaurant_y customer_x customer_y "
                f"(got {len(parts)})"
            )
        values: List[int] = []
        for part in parts:
            try:
                values.append(int(part))
            except ValueError:
                raise ValueError(f"'{part}' is not an integer") from None
        return values

    @staticmethod
    def validate_coordinates(values: Sequence[int]) -> List[int]:
        """Ensure every coordinate lies within the accepted input range.

        Args:
            values: Integers to validate.

        Returns:
            The same values as a list.

        Raises:
            ValueError: If any value is outside 0..1000.
        """
        for value in values:
            if not COORD_MIN <= value <= COORD_MAX:
                raise ValueError(
                    f"coordinate {value} is out of range ({COORD_MIN}-{COORD_MAX})"
                )
        return list(values)

    @staticmethod
    def parse_count(tokens: Sequence[str], default: int = 1, maximum: int = 10000) -> int:
        """Parse an optional positive integer argument.

        Args:
            tokens: Argument tokens.
            default: Value used when no argument is given.
            maximum: Upper bound.

        Returns:
            Parsed count.

        Raises:
            ValueError: If the argument is not a positive integer within range.
        """
        if not tokens:
            return default
        try:
            count = int(tokens[0])
        except ValueError:
            raise ValueError(f"'{tokens[0]}' is not an integer") from None
        if not 1 <= count <= maximum:
            raise ValueError(f"count must be between 1 and {maximum}")
        return count
