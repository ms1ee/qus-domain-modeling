"""Command parsing and input validation."""

from collections import deque

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status", "t": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "wait": "tick", "w": "tick", "n": "tick",
    "history": "history", "hist": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}

HELP_TEXT = """Commands (shortcut in brackets):
  start [s]   [rx ry cx cy]  create an order (coordinates 0-800)
  status [t]                 system funds and rider status
  orders [o]                 all orders
  riders [r]                 rider status change log
  map [m]                    ASCII map of riders and orders
  tick [n] [N]               advance N ticks (default 1)
  history                    show command history (!N repeats entry N)
  help [h]                   this help
  quit / exit [q]            leave the program
Every command (except help/history/quit) advances the simulation one tick."""


class InputManager:
    """Reads commands, keeps history and validates input."""

    def __init__(self, max_history=200):
        """Create the manager with a bounded history."""
        self.history = deque(maxlen=max_history)

    def read_line(self, prompt):
        """Read a raw line from stdin."""
        return input(prompt)

    def read_command(self, prompt="dispatch> "):
        """Read a command line, resolving ``!N`` history recalls."""
        line = self.read_line(prompt).strip()
        if line.startswith("!") and line[1:].isdigit():
            idx = int(line[1:]) - 1
            if 0 <= idx < len(self.history):
                line = self.history[idx]
                print("> " + line)
            else:
                raise ValueError("No history entry %s" % line[1:])
        if line:
            self.history.append(line)
        return line

    @staticmethod
    def parse_command(line):
        """Split a line into ``(command, args)``; unknown commands keep name."""
        parts = line.replace(",", " ").split()
        if not parts:
            return "", []
        name = parts[0].lower()
        return COMMAND_ALIASES.get(name, name), parts[1:]

    @staticmethod
    def validate_coordinates(tokens, low=0, high=800):
        """Validate four integer coordinates.

        :return: ``(coords, None)`` on success or ``(None, error_message)``.
        """
        cleaned = []
        for tok in tokens:
            tok = tok.strip().strip("[]()")
            if tok:
                cleaned.extend(t for t in tok.replace(",", " ").split() if t)
        if len(cleaned) != 4:
            return None, ("Expected 4 integers: restaurant_x restaurant_y "
                          "customer_x customer_y (got %d)" % len(cleaned))
        coords = []
        for tok in cleaned:
            try:
                value = int(tok)
            except ValueError:
                return None, "'%s' is not an integer" % tok
            if not low <= value <= high:
                return None, "Coordinate %d out of range %d-%d" % (value, low,
                                                                   high)
            coords.append(value)
        return coords, None

    @staticmethod
    def parse_tick_count(args, maximum=1000):
        """Parse the optional tick count argument."""
        if not args:
            return 1, None
        try:
            n = int(args[0])
        except ValueError:
            return None, "Tick count must be an integer"
        if not 1 <= n <= maximum:
            return None, "Tick count must be between 1 and %d" % maximum
        return n, None
