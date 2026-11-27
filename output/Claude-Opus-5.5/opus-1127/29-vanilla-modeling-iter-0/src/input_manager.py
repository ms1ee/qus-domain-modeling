"""Command parsing and input validation."""

import logging

logger = logging.getLogger(__name__)

HELP_TEXT = """Commands:
  start [rx ry cx cy]  (s)   create an order (coordinates 0-800)
  status               (st)  system snapshot
  orders               (o)   all orders
  riders               (r)   rider status-change history
  map                  (m)   show map
  tick [n]             (t)   advance simulation n ticks (default 1)
  save [path]                save state to JSON
  history              (hi)  command history
  help                 (h)   this help
  quit / exit          (q)   exit"""

SHORTCUTS = {
    "s": "start", "st": "status", "o": "orders", "r": "riders",
    "m": "map", "t": "tick", "hi": "history", "h": "help", "?": "help",
    "q": "quit", "exit": "quit",
}


class InputManager:
    """Parses commands and dispatches them to the system."""

    def __init__(self, system, display, input_func=input):
        self.system = system
        self.display = display
        self.input_func = input_func
        self.command_history = []

    @staticmethod
    def parse_coordinates(text):
        """Parse four integer coordinates in 0-800 from text.

        Accepts formats like ``1 2 3 4``, ``1,2,3,4`` or ``[1, 2, 3, 4]``.
        Raises ValueError with a friendly message on failure.
        """
        cleaned = text.replace("[", " ").replace("]", " ").replace(",", " ")
        parts = cleaned.split()
        if len(parts) != 4:
            raise ValueError("Expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y")
        values = []
        for p in parts:
            try:
                v = int(p)
            except ValueError:
                raise ValueError("'%s' is not an integer" % p)
            if v < 0 or v > 800:
                raise ValueError("Coordinate %d out of range 0-800" % v)
            values.append(v)
        return values

    def handle(self, line):
        """Process one command line and return the output text."""
        line = (line or "").strip()
        if not line:
            return ""
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        tokens = line.split(None, 1)
        cmd = tokens[0].lower()
        cmd = SHORTCUTS.get(cmd, cmd)
        arg = tokens[1] if len(tokens) > 1 else ""
        try:
            if cmd == "start":
                if not arg:
                    arg = self.input_func(
                        "Enter restaurant_x restaurant_y customer_x customer_y: ")
                coords = self.parse_coordinates(arg)
                order, rider, new_rider = self.system.create_order(*coords)
                return self.display.show_start_result(self.system, order,
                                                      rider, new_rider)
            if cmd == "status":
                return self.display.show_status(self.system)
            if cmd == "orders":
                return self.display.show_orders(self.system)
            if cmd == "riders":
                return self.display.show_riders(self.system)
            if cmd == "map":
                return self.display.render_map(self.system)
            if cmd == "tick":
                n = int(arg) if arg else 1
                if n < 0 or n > 100000:
                    raise ValueError("tick count must be 0-100000")
                self.system.advance(n)
                return "Advanced %d tick(s). Now tick %d." % (n, self.system.tick)
            if cmd == "save":
                path = self.system.save_state(arg or None)
                return "State saved to %s" % path
            if cmd == "history":
                return "\n".join("%3d  %s" % (i + 1, c)
                                 for i, c in enumerate(self.command_history))
            if cmd == "help":
                return HELP_TEXT
            if cmd == "quit":
                self.system.stop()
                return "Goodbye."
            return "Unknown command '%s'. Type 'help'." % tokens[0]
        except ValueError as exc:
            return "Error: %s" % exc
        except (EOFError, KeyboardInterrupt):
            return "Input cancelled."
        except Exception as exc:  # graceful recovery
            logger.exception("Command failed")
            self.system.check_consistency()
            return "Unexpected error: %s (state recovered)" % exc
