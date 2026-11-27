"""Command parsing, shortcut resolution, command history and input validation."""

from __future__ import annotations

import logging
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:  # Enables arrow-key history on platforms that provide readline.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows without pyreadline
    readline = None  # type: ignore[assignment]

MIN_COORDINATE = 0
MAX_COORDINATE = 800


class InputManager:
    """Reads user lines, resolves shortcut keys and validates coordinates."""

    ALIASES = {
        "start": "start", "s": "start",
        "status": "status", "st": "status",
        "orders": "orders", "o": "orders",
        "riders": "riders", "r": "riders",
        "map": "map", "m": "map",
        "tick": "tick", "t": "tick",
        "run": "run", "u": "run",
        "history": "history", "hist": "history",
        "help": "help", "h": "help", "?": "help",
        "quit": "quit", "exit": "quit", "q": "quit",
        "!!": "!!",
    }

    MAX_HISTORY = 200

    def __init__(self, reader: Callable[[str], str] = input) -> None:
        """Create the input manager.

        Args:
            reader: Function used to read a line (``input`` by default).
        """
        self._reader = reader
        self.history: List[str] = []

    def read_line(self, prompt: str = "dispatch> ") -> str:
        """Read one stripped line of user input."""
        return self._reader(prompt).strip()

    def parse(self, line: str) -> Tuple[str, List[str]]:
        """Split a line into a canonical command name and its arguments.

        Args:
            line: Raw user input.

        Returns:
            Tuple of (command name, argument tokens). The command name is
            empty if the line is blank.
        """
        tokens = line.split()
        if not tokens:
            return "", []
        word = tokens[0].lower()
        return self.ALIASES.get(word, word), tokens[1:]

    def record(self, line: str) -> None:
        """Store a command in the in-session history."""
        if not line or line == "!!":
            return
        if self.history and self.history[-1] == line:
            return
        self.history.append(line)
        if len(self.history) > self.MAX_HISTORY:
            del self.history[0]

    def last_command(self) -> Optional[str]:
        """Return the most recent recorded command, if any."""
        return self.history[-1] if self.history else None

    @staticmethod
    def parse_coordinates(tokens: List[str]) -> List[int]:
        """Parse four integer coordinates from command arguments.

        Accepts whitespace or comma separators and optional brackets.

        Args:
            tokens: Argument tokens.

        Returns:
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: With a descriptive message if the input is invalid.
        """
        text = " ".join(tokens).replace(",", " ").replace("[", " ").replace("]", " ")
        parts = text.split()
        if len(parts) != 4:
            raise ValueError(
                "expected four integers: restaurant_x restaurant_y customer_x customer_y "
                f"(got {len(parts)} value(s))")
        values: List[int] = []
        labels = ("restaurant x", "restaurant y", "customer x", "customer y")
        for label, part in zip(labels, parts):
            try:
                value = int(part)
            except ValueError as exc:
                raise ValueError(f"{label} '{part}' is not an integer") from exc
            if not MIN_COORDINATE <= value <= MAX_COORDINATE:
                raise ValueError(
                    f"{label} {value} is out of range {MIN_COORDINATE}-{MAX_COORDINATE}")
            values.append(value)
        return values

    def prompt_coordinates(self) -> List[int]:
        """Interactively ask for the four coordinates and validate them."""
        line = self._reader(
            "Enter restaurant_x restaurant_y customer_x customer_y (0-800): ").strip()
        return self.parse_coordinates(line.split())
