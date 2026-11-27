"""Command parsing, input validation and command history.

Supported shortcuts: ``s`` start, ``st`` status, ``o`` orders, ``r`` riders,
``m`` map, ``t`` step, ``w`` save, ``h`` help, ``q`` quit. ``!!`` repeats the
last command and ``!n`` re-runs history entry n (1-based). If the readline
module is available, arrow keys browse history.
"""

import logging
from typing import Callable, List, Optional, Tuple

from pathplanner import MAP_SIZE

logger = logging.getLogger(__name__)

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "step",
    "w": "save",
    "h": "help",
    "?": "help",
    "q": "quit",
    "exit": "quit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order (restaurant x y, customer x y; 0-800)
                       (s = shortcut)
  status               Funds, riders and their orders (st)
  orders               All orders with time, distance and rider (o)
  riders               Every rider status change log (r)
  map                  ASCII map of riders and active orders (m)
  step [n]             Advance the simulation by n ticks (default 1) (t)
  save [path]          Save the system state as JSON (w)
  help                 Show this help (h, ?)
  quit                 Exit the program (q, exit)
History: !! repeats the last command, !n repeats history entry n."""


class InputManager:
    """Reads and validates user commands."""

    def __init__(self, input_func: Optional[Callable[[str], str]] = None,
                 output_func: Optional[Callable[[str], None]] = None) -> None:
        """Create the input manager.

        Args:
            input_func: Function used to read a line (defaults to ``input``).
            output_func: Function used to print messages (defaults to ``print``).
        """
        self._input = input_func or input
        self._output = output_func or print
        self.history: List[str] = []
        self._setup_readline()

    @staticmethod
    def _setup_readline() -> None:
        """Enable arrow-key history editing when readline is available."""
        try:
            import readline  # noqa: F401  (imported for its side effects)
        except ImportError:
            logger.debug("readline not available; history editing disabled")

    def read_command(self, prompt: str = "> ") -> Tuple[str, List[str]]:
        """Read one command line and split it into name and arguments.

        Args:
            prompt: Prompt shown to the user.

        Returns:
            Tuple ``(command_name, args)``. The name is empty if nothing
            usable was entered.

        Raises:
            EOFError: If input is closed.
        """
        raw = self._input(prompt).strip()
        if not raw:
            return "", []
        if raw == "!!":
            if not self.history:
                self._output("No command in history.")
                return "", []
            raw = self.history[-1]
        elif raw.startswith("!") and raw[1:].isdigit():
            index = int(raw[1:])
            if not 1 <= index <= len(self.history):
                self._output(f"History entry {index} does not exist.")
                return "", []
            raw = self.history[index - 1]
        self.history.append(raw)
        tokens = raw.split()
        name = tokens[0].lower()
        name = ALIASES.get(name, name)
        return name, tokens[1:]

    def parse_coordinates(self, tokens: List[str]) -> List[int]:
        """Parse and validate four order coordinates.

        Accepts whitespace- or comma-separated values.

        Args:
            tokens: Raw tokens such as ``["10", "20", "300", "400"]``.

        Returns:
            List of four integers ``[rx, ry, cx, cy]``.

        Raises:
            ValueError: With a user-facing message on invalid input.
        """
        text = " ".join(tokens).replace(",", " ")
        parts = text.split()
        if len(parts) != 4:
            raise ValueError(
                f"expected 4 integers (restaurant_x restaurant_y customer_x customer_y), got {len(parts)}"
            )
        values: List[int] = []
        for part in parts:
            try:
                value = int(part)
            except ValueError:
                raise ValueError(f"'{part}' is not an integer") from None
            if not 0 <= value <= MAP_SIZE:
                raise ValueError(f"{value} is out of range 0-{MAP_SIZE}")
            values.append(value)
        return values

    def prompt_coordinates(self) -> Optional[List[int]]:
        """Interactively ask the user for four coordinates.

        Returns:
            The validated coordinates, or None if the user cancels with an
            empty line.
        """
        self._output("Enter restaurant_x restaurant_y customer_x customer_y "
                     "(0-800), or press Enter to cancel:")
        while True:
            line = self._input("order> ").strip()
            if not line:
                return None
            try:
                return self.parse_coordinates(line.split())
            except ValueError as exc:
                self._output(f"Invalid input: {exc}. Try again.")

    @staticmethod
    def parse_positive_int(tokens: List[str], default: int, maximum: int) -> int:
        """Parse an optional positive integer argument.

        Args:
            tokens: Argument tokens.
            default: Value used when no token is given.
            maximum: Largest allowed value.

        Returns:
            The parsed integer.

        Raises:
            ValueError: If the value is not an integer or is out of range.
        """
        if not tokens:
            return default
        try:
            value = int(tokens[0])
        except ValueError:
            raise ValueError(f"'{tokens[0]}' is not an integer") from None
        if not 1 <= value <= maximum:
            raise ValueError(f"step count must be between 1 and {maximum}")
        return value

    @staticmethod
    def help_text() -> str:
        """Return the help text listing all commands."""
        return HELP_TEXT
