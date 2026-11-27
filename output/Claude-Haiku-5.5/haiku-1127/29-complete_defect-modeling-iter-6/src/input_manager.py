"""Command parsing, shortcut keys, command history and input validation."""

import logging
from typing import Callable, List, Tuple

from grid import MAX_COORDINATE, MIN_COORDINATE

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "history": "history", "hist": "history",
    "save": "save",
    "help": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}

COORDINATE_LABELS = ("restaurant_x", "restaurant_y",
                     "customer_x", "customer_y")

PROMPT_TEXT = ("Enter restaurant_x restaurant_y customer_x customer_y "
               "(0-800, or 'cancel'): ")


class InputManager:
    """Reads, parses and validates user commands.

    Attributes:
        command_history: Raw command lines entered so far.
        min_coordinate: Smallest accepted coordinate.
        max_coordinate: Largest accepted coordinate.
    """

    def __init__(self, min_coordinate: int = MIN_COORDINATE,
                 max_coordinate: int = MAX_COORDINATE,
                 input_func: Callable[[str], str] = input,
                 output_func: Callable[[str], None] = print) -> None:
        """Create the input manager.

        Args:
            min_coordinate: Smallest accepted coordinate value.
            max_coordinate: Largest accepted coordinate value.
            input_func: Function used to read a line (injectable).
            output_func: Function used to print messages (injectable).
        """
        self.command_history: List[str] = []
        self.min_coordinate = min_coordinate
        self.max_coordinate = max_coordinate
        self.input_func = input_func
        self.output_func = output_func

    def read_command(self, prompt: str = "dispatch> ") -> str:
        """Read one command line. ``!!`` repeats the previous command.

        Args:
            prompt: Prompt shown to the user.

        Returns:
            The stripped command text (may be empty).

        Raises:
            ValueError: If ``!!`` is used with an empty history.
        """
        raw = self.input_func(prompt).strip()
        if raw == "!!":
            if not self.command_history:
                raise ValueError("No previous command to repeat.")
            raw = self.command_history[-1]
            self.output_func(f"Repeating: {raw}")
        if raw:
            self.command_history.append(raw)
        return raw

    def parse_command(self, line: str) -> Tuple[str, List[str]]:
        """Split a command line into a canonical command name and arguments.

        Args:
            line: The raw command line.

        Returns:
            Tuple ``(command_name, arguments)``.

        Raises:
            ValueError: If the command is empty or unknown.
        """
        tokens = line.split()
        if not tokens:
            raise ValueError("Empty command.")
        name = COMMAND_ALIASES.get(tokens[0].lower())
        if name is None:
            raise ValueError(
                f"Unknown command '{tokens[0]}'. Type 'help' for the list.")
        return name, tokens[1:]

    def validate_coordinate(self, text, label: str = "coordinate") -> int:
        """Validate that text is an integer within the coordinate range.

        Args:
            text: Text typed by the user.
            label: Field name for error messages.

        Returns:
            The integer value.

        Raises:
            ValueError: If the text is not an integer or is out of range.
        """
        try:
            value = int(str(text).strip())
        except ValueError:
            raise ValueError(
                f"{label} must be an integer, got '{text}'") from None
        if not self.min_coordinate <= value <= self.max_coordinate:
            raise ValueError(
                f"{label} {value} is out of range "
                f"{self.min_coordinate}-{self.max_coordinate}")
        return value

    def parse_coordinates(self, tokens: List[str]) -> List[int]:
        """Return the four validated order coordinates.

        If no tokens are given the user is prompted. Values may be separated
        by spaces or commas.

        Args:
            tokens: Arguments following the start command.

        Returns:
            List ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the input is cancelled, malformed or out of range.
        """
        if tokens:
            text = " ".join(tokens)
        else:
            text = self.input_func(PROMPT_TEXT).strip()
            if text.lower() == "cancel":
                raise ValueError("Order cancelled.")
        parts = text.replace(",", " ").split()
        if len(parts) != 4:
            raise ValueError(
                f"Expected 4 integer coordinates, got {len(parts)}. "
                "Format: restaurant_x restaurant_y customer_x customer_y")
        return [self.validate_coordinate(part, label)
                for part, label in zip(parts, COORDINATE_LABELS)]

    def help_text(self) -> str:
        """Return the command help text."""
        return "\n".join([
            "Commands (shortcut in brackets):",
            "  start [rx ry cx cy] [s]  Place an order (restaurant, customer)",
            "  status [st]              Funds, riders and their orders",
            "  orders [o]               Details of all orders",
            "  riders [r]               Status-change log of all riders",
            "  map [m]                  Show the ASCII map",
            "  tick [n] [t]             Advance simulated time n ticks",
            "  history [hist]           Show command history",
            "  save [path]              Save state to a JSON file",
            "  help [?]                 Show this help",
            "  quit [exit, q]           Save and exit",
            "  !!                       Repeat the previous command",
            f"Coordinates must be integers in {self.min_coordinate}-"
            f"{self.max_coordinate}.",
        ])
