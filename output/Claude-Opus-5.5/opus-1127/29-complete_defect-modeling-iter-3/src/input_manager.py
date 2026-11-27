"""Command parsing, shortcuts, history and input validation."""

import re

from grid_map import MAP_SIZE

SHORTCUTS = {
    "s": "start", "n": "start", "new": "start", "start": "start",
    "st": "status", "status": "status",
    "o": "orders", "orders": "orders",
    "r": "riders", "riders": "riders",
    "m": "map", "map": "map",
    "t": "tick", "tick": "tick",
    "h": "help", "?": "help", "help": "help",
    "hist": "history", "history": "history",
    "c": "check", "check": "check",
    "save": "save", "load": "load",
    "q": "quit", "quit": "quit", "exit": "quit",
}

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] (s)  place an order: restaurant x,y + customer x,y (0-800)
  status (st)              system funds and rider states
  orders (o)               all order details
  riders (r)               rider status-change history
  map (m)                  ASCII map of riders and active orders
  tick [n] (t)             advance the simulation n ticks (empty line = 1 tick)
  check (c)                run a system consistency check
  save [file] / load [file]  persist / restore state as JSON
  history (hist), !n       show command history / repeat command n
  help (h, ?)              this help
  quit / exit (q)          leave the program"""


class InputManager:
    """Parses commands and validates user input."""

    def __init__(self):
        self.command_history = []

    def parse(self, line):
        """Return (command, args). Empty input returns (None, [])."""
        line = (line or "").strip()
        if not line:
            return None, []
        if line.startswith("!"):
            try:
                n = int(line[1:])
                line = self.command_history[n - 1]
            except (ValueError, IndexError):
                raise ValueError("No such history entry: %s" % line)
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        parts = line.split(None, 1)
        word = parts[0].lower()
        if word not in SHORTCUTS:
            raise ValueError("Unknown command '%s'. Type 'help'." % word)
        rest = parts[1] if len(parts) > 1 else ""
        return SHORTCUTS[word], rest.split() if rest else []

    @staticmethod
    def parse_coordinates(text):
        """Parse four integer coordinates (0-800) from text.

        Accepts space or comma separated values, optionally in brackets.
        """
        cleaned = re.sub(r"[\[\]()]", " ", text or "")
        tokens = [t for t in re.split(r"[\s,]+", cleaned) if t]
        if len(tokens) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y")
        values = []
        for tok in tokens:
            try:
                v = int(tok)
            except ValueError:
                raise ValueError("'%s' is not an integer" % tok)
            if v < 0 or v > MAP_SIZE:
                raise ValueError("Coordinate %d out of range 0-%d"
                                 % (v, MAP_SIZE))
            values.append(v)
        return values

    @staticmethod
    def parse_count(args, default=1):
        """Parse an optional positive integer count."""
        if not args:
            return default
        try:
            n = int(args[0])
        except ValueError:
            raise ValueError("Tick count must be an integer")
        if n < 1 or n > 100000:
            raise ValueError("Tick count must be between 1 and 100000")
        return n

    def history_text(self):
        if not self.command_history:
            return "History is empty."
        return "\n".join("%3d  %s" % (i + 1, c)
                         for i, c in enumerate(self.command_history))
