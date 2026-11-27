"""Command parsing, shortcut handling, history and input validation."""

import logging
from typing import Callable, List, Optional, Tuple

from order import validate_coordinates

logger = logging.getLogger(__name__)

COMMANDS = (
    "start",
    "status",
    "orders",
    "riders",
    "map",
    "wait",
    "save",
    "history",
    "help",
    "quit",
    "exit",
)

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "w": "wait",
    "f": "save",
    "hi": "history",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant then customer, 0-800). Prompts if omitted.
  status               Show funds, riders and their current state, plus the map.
  orders               Show all orders with timing, distance and rider.
  riders               Show the event log (spawn, accepted, arrived, delivered) per rider.
  map                  Show the ASCII street map with riders and active orders.
  wait [n]             Let n extra ticks pass (every command already advances one tick).
  save [file]          Save system state to a JSON file (default dispatch_state.json).
  history              Show recent commands.
  help                 Show this help.
  quit / exit          Leave the simulator.
Shortcuts: s=start st=status o=orders r=riders m=map w=wait f=save h=help q=quit
History: !! repeats the last command, !n repeats command number n from 'history'.
"""


class InputManager:
    """Reads, expands and validates user commands."""

    def __init__(
        self,
        reader: Callable[[str], str] = input,
        prompt: str = "dispatch> ",
        max_history: int = 100,
    ) -> None:
        """Create an input manager.

        Args:
            reader: Function used to read a line (``input`` by default).
            prompt: Prompt shown for each command.
            max_history: Number of commands kept in the history.
        """
        self._reader = reader
        self._prompt = prompt
        self._max_history = max_history
        self._history: List[str] = []
        self._readline = None
        try:
            import readline  # noqa: F401  (enables line editing and history on POSIX)

            self._readline = readline
        except ImportError:
            logger.debug("readline not available; line editing disabled")

    @property
    def history(self) -> List[str]:
        """Return a copy of the command history (oldest first)."""
        return list(self._history)

    def read_raw(self, prompt: Optional[str] = None) -> str:
        """Read one raw line of input."""
        return self._reader(prompt if prompt is not None else self._prompt)

    def read_command(self) -> Tuple[str, List[str]]:
        """Read and parse one command line.

        Returns:
            ``(command, arguments)``. ``command`` is an empty string for a blank
            line.

        Raises:
            ValueError: For unknown commands or invalid history references.
        """
        line = self._expand_history(self.read_raw().strip())
        if not line:
            return "", []
        self._remember(line)
        tokens = line.split()
        word = tokens[0].lower()
        command = ALIASES.get(word, word)
        if command not in COMMANDS:
            raise ValueError(f"unknown command '{tokens[0]}'. Type 'help' for a list of commands.")
        return command, tokens[1:]

    def _expand_history(self, raw: str) -> str:
        """Expand ``!!`` and ``!n`` history references."""
        if raw == "!!":
            if not self._history:
                raise ValueError("no previous command in history")
            return self._history[-1]
        if raw.startswith("!") and raw[1:].isdigit():
            index = int(raw[1:])
            if not 1 <= index <= len(self._history):
                raise ValueError(f"history entry {index} does not exist")
            return self._history[index - 1]
        return raw

    def _remember(self, line: str) -> None:
        """Append a command to the history, trimming old entries."""
        self._history.append(line)
        if len(self._history) > self._max_history:
            del self._history[0 : len(self._history) - self._max_history]

    def parse_order_args(self, args: List[str]) -> List[int]:
        """Return validated order coordinates from arguments or a prompt.

        Raises:
            ValueError: If the input is not exactly four integers in range.
        """
        tokens = list(args)
        if not tokens:
            tokens = self.read_raw(
                "Enter restaurant_x restaurant_y customer_x customer_y (0-800): "
            ).split()
        if len(tokens) != 4:
            raise ValueError(f"start needs exactly 4 integers, got {len(tokens)}")
        return validate_coordinates(tokens)

    @staticmethod
    def help_text() -> str:
        """Return the command help text."""
        return HELP_TEXT
