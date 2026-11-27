"""Command parsing, validation and dispatch."""

import logging

try:
    from . import config
    from . import persistence
except ImportError:  # pragma: no cover
    import config
    import persistence

logger = logging.getLogger(__name__)

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] (s)  place an order: restaurant x y, customer x y
  status (st)              system funds and rider states
  orders (o)               all order details
  riders (r)               rider status change history
  map (m)                  show the ASCII map
  tick [n] (t)             advance the simulation n ticks (default 1)
  history (hi)             show command history; !N repeats command N
  save [file] / load [file]  persist / restore state as JSON
  help (h, ?)              show this help
  quit / exit (q)          exit the program
Every command also advances the simulation by one tick."""

ALIASES = {
    "s": "start", "start": "start",
    "st": "status", "status": "status",
    "o": "orders", "orders": "orders",
    "r": "riders", "riders": "riders",
    "m": "map", "map": "map",
    "t": "tick", "tick": "tick",
    "hi": "history", "history": "history",
    "h": "help", "?": "help", "help": "help",
    "save": "save", "load": "load",
    "q": "quit", "quit": "quit", "exit": "quit",
}


class InputError(ValueError):
    """Raised for invalid user input."""


class InputManager:
    """Parses commands, validates input and executes actions."""

    def __init__(self, system, display, input_func=input,
                 state_file="dispatch_state.json"):
        self.system = system
        self.display = display
        self.input_func = input_func
        self.command_history = []
        self.state_file = state_file

    @staticmethod
    def parse_coordinates(tokens):
        """Validate four integer coordinates in [COORD_MIN, COORD_MAX]."""
        if isinstance(tokens, str):
            tokens = tokens.replace(",", " ").replace("[", " ") \
                .replace("]", " ").split()
        if len(tokens) != 4:
            raise InputError("Please enter exactly 4 integers: "
                             "restaurant_x restaurant_y customer_x customer_y")
        values = []
        for t in tokens:
            try:
                v = int(t)
            except (TypeError, ValueError):
                raise InputError("'%s' is not an integer." % t)
            if not config.COORD_MIN <= v <= config.COORD_MAX:
                raise InputError("Coordinate %d out of range (%d-%d)."
                                 % (v, config.COORD_MIN, config.COORD_MAX))
            values.append(v)
        return values

    def handle(self, line):
        """Execute a command line and return (output_text, advance_tick)."""
        line = (line or "").strip()
        if not line:
            return "", True
        if line.startswith("!"):
            try:
                idx = int(line[1:]) - 1
                line = self.command_history[idx]
            except (ValueError, IndexError):
                return "Invalid history reference.", False
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        parts = line.split()
        cmd = ALIASES.get(parts[0].lower())
        args = parts[1:]
        if cmd is None:
            return "Unknown command '%s'. Type 'help'." % parts[0], False
        try:
            return getattr(self, "_cmd_" + cmd)(args)
        except InputError as exc:
            return "Error: %s" % exc, False
        except Exception as exc:  # pragma: no cover - recovery
            logger.exception("Command failed")
            problems = self.system.check_consistency()
            return "Unexpected error: %s (recovered; %d issue(s) fixed)" % (
                exc, len(problems)), False

    # commands -------------------------------------------------------------
    def _cmd_start(self, args):
        if not args:
            raw = self.input_func("Enter restaurant_x restaurant_y "
                                  "customer_x customer_y: ")
            values = self.parse_coordinates(raw)
        else:
            values = self.parse_coordinates(args)
        info = self.system.order_manager.place_order(*values)
        return self.display.start_result_text(info), True

    def _cmd_status(self, args):
        return self.display.status_text(), True

    def _cmd_orders(self, args):
        return self.display.orders_text(), True

    def _cmd_riders(self, args):
        return self.display.riders_text(), True

    def _cmd_map(self, args):
        return self.display.render_map(), True

    def _cmd_tick(self, args):
        n = 1
        if args:
            try:
                n = int(args[0])
            except ValueError:
                raise InputError("tick expects an integer")
            if n < 0 or n > 100000:
                raise InputError("tick count must be in 0-100000")
        self.system.tick(n)
        return "Advanced %d tick(s); now t=%d." % (
            n, self.system.current_tick), False

    def _cmd_history(self, args):
        return "\n".join("%3d  %s" % (i + 1, c)
                         for i, c in enumerate(self.command_history)), False

    def _cmd_help(self, args):
        return HELP_TEXT, False

    def _cmd_save(self, args):
        path = args[0] if args else self.state_file
        try:
            persistence.save_state(path)
        except OSError as exc:
            raise InputError("could not save: %s" % exc)
        return "State saved to %s" % path, False

    def _cmd_load(self, args):
        path = args[0] if args else self.state_file
        try:
            nr, no = persistence.load_state(path)
        except (OSError, ValueError, KeyError) as exc:
            raise InputError("could not load: %s" % exc)
        return "Loaded %d rider(s) and %d order(s) from %s" % (nr, no, path), \
            False

    def _cmd_quit(self, args):
        self.system.stop()
        return "Bye.", False
