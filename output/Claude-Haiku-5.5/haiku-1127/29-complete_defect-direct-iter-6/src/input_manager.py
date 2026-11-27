"""Command parsing, input validation, history and the interactive loop."""

import logging

import globalvar
from display import DisplayManager
from geometry import MAP_SIZE, validate_coordinate, validate_point, to_cell
from order import OrderManager
from system import SystemManager

try:  # Enables line editing and arrow-key history on supported platforms.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

logger = logging.getLogger("dispatch.input")

WELCOME = (
    "Food Delivery Dispatch Simulator\n"
    "Type 'help' for a list of commands."
)

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant x y, customer x y; 0-800).
                       Prompts for the values if they are not given.
  status  (s)          Show funds, tick and every rider's state and orders.
  orders  (o)          Show details for all orders.
  riders  (r)          Show every recorded rider status change.
  map     (m)          Show the 8x8 ASCII map.
  save [file]          Save parameters, riders and orders as JSON.
  history              Show command history.
  !! / !N              Repeat the last command / command number N.
  help    (h, ?)       Show this help.
  quit    (q, exit)    Exit the program."""

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
    "hist": "history",
}

POINT_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")
DEFAULT_SAVE_FILE = "dispatch_state.json"


class InputManager:
    """Reads commands from the user and dispatches them."""

    def __init__(self, input_func=None, output_func=None):
        """Create the interface.

        Args:
            input_func: Callable used to read a line (defaults to ``input``).
            output_func: Callable used to print text (defaults to ``print``).
        """
        self.input_func = input_func or input
        self.output_func = output_func or print
        self.display = DisplayManager()
        self.system = SystemManager()
        self.orders = OrderManager()
        self.history = []

    def say(self, text=""):
        """Write a line of output."""
        self.output_func(text)

    def run(self):
        """Run the interactive loop until the system is stopped or input ends."""
        self.say(WELCOME)
        while globalvar.get_value("running", True):
            try:
                line = self.input_func("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self.say("")
                break
            self.process_line(line)
        self.say("Goodbye.")

    def process_line(self, line):
        """Handle one raw input line, including history expansion and errors."""
        text = (line or "").strip()
        if not text:
            return
        expanded = self.expand_history(text)
        if expanded is None:
            return
        self.history.append(expanded)
        try:
            self.execute(expanded)
        except ValueError as exc:
            self.say(f"Input error: {exc}")
        except Exception:  # pragma: no cover - defensive
            logger.exception("unexpected error while executing '%s'", expanded)
            self.say("Unexpected internal error; the system state was preserved. See the log for details.")

    def expand_history(self, text):
        """Expand '!!' and '!N' references; return None when expansion fails."""
        if text == "!!":
            if not self.history:
                self.say("No command history yet.")
                return None
            return self.history[-1]
        if text.startswith("!") and text[1:].isdigit():
            index = int(text[1:]) - 1
            if 0 <= index < len(self.history):
                return self.history[index]
            self.say(f"No history entry {text[1:]}.")
            return None
        return text

    def execute(self, text):
        """Parse and run a single command."""
        parts = text.split()
        name = parts[0].lower()
        name = ALIASES.get(name, name)
        args = parts[1:]
        if name == "start":
            self.cmd_start(args)
        elif name == "status":
            self.cmd_status()
        elif name == "orders":
            self.say(self.display.format_orders(self.orders.all_orders()))
        elif name == "riders":
            self.say(self.display.format_rider_logs(self.system.riders()))
        elif name == "map":
            self.say(self.display.render_map(self.system.riders(), self.orders.all_orders()))
        elif name == "save":
            self.cmd_save(args)
        elif name == "history":
            for index, item in enumerate(self.history, start=1):
                self.say(f"  {index}: {item}")
        elif name == "help":
            self.say(HELP_TEXT)
        elif name in ("quit", "exit"):
            self.system.stop()
        else:
            self.say(f"Unknown command '{parts[0]}'. Type 'help' for a list of commands.")

    def cmd_status(self):
        """Print the status snapshot and any consistency problems."""
        self.say(self.display.format_status(self.system.funds, globalvar.get_value("tick", 0), self.system.riders()))
        issues = self.system.check_consistency()
        for issue in issues:
            self.say(f"Warning: {issue}")

    def cmd_save(self, args):
        """Save the current state to a JSON file."""
        path = args[0] if args else DEFAULT_SAVE_FILE
        try:
            self.system.save_state(path)
        except OSError as exc:
            self.say(f"Could not save state: {exc}")
            return
        self.say(f"State saved to {path}.")

    def cmd_start(self, args):
        """Create an order, assign it, simulate delivery and print the route."""
        if args and len(args) != 4:
            raise ValueError("start expects four integers: restaurant x y, customer x y")
        if args:
            values = [self._parse_int(token, label) for token, label in zip(args, POINT_LABELS)]
        else:
            values = [self._prompt_int(label) for label in POINT_LABELS]
        restaurant = validate_point(values[0:2], "restaurant")
        customer = validate_point(values[2:4], "customer")

        new_riders = self.system.check_recruitment()
        order = self.orders.create_order(list(restaurant), list(customer))
        rider = self.orders.assign_order(order)

        res_cell = to_cell(restaurant)
        cus_cell = to_cell(customer)
        self.say(f"Order #{order.id} accepted.")
        self.say(f"  Restaurant: position {restaurant}, grid cell (col {res_cell[0]}, row {res_cell[1]})")
        self.say(f"  Customer:   position {customer}, grid cell (col {cus_cell[0]}, row {cus_cell[1]})")
        if new_riders:
            ids = ", ".join(str(r.rider_id) for r in new_riders)
            self.say(f"  New rider added: yes (rider {ids})")
        else:
            self.say("  New rider added: no")
        if rider is None:
            self.say("  No rider is available yet; the order is pending until a rider is recruited.")

        completed = self.system.run_until_complete(order)
        assigned = self.system.get_rider(order.rider_id) if order.rider_id is not None else None
        if assigned is not None:
            self.say(
                f"  Assigned rider: {assigned.rider_id} (speed {assigned.speed} units/tick)"
            )
            self.say(self.display.format_route_map(order, assigned))
        if completed:
            self.say(
                f"  Delivered to customer at tick {order.complete_tick}: "
                f"time taken {order.time_taken} ticks, distance {order.distance} units, "
                f"efficiency {order.efficiency} units/tick."
            )
        else:
            self.say("  Order not completed within the tick limit; use 'orders' to check its status.")

    def _parse_int(self, token, label):
        """Parse and validate one coordinate token."""
        try:
            value = int(token)
        except ValueError as exc:
            raise ValueError(f"{label} must be an integer, got '{token}'") from exc
        return validate_coordinate(value, label)

    def _prompt_int(self, label):
        """Prompt until a valid coordinate is entered or the user cancels."""
        while True:
            raw = self.input_func(f"  {label} (0-{MAP_SIZE}): ").strip()
            if raw.lower() in ("cancel", "q"):
                raise ValueError("order entry cancelled")
            try:
                return self._parse_int(raw, label)
            except ValueError as exc:
                self.say(f"  {exc}. Try again or type 'cancel'.")
