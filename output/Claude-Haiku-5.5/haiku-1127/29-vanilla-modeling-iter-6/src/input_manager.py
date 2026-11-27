"""Command-line parsing, validation and dispatch for the simulator."""

import logging
import math

from grid_map import MAP_SIZE, Point, is_valid_coordinate

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "w": "save",
    "hist": "history",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order (restaurant then customer, 0-800) and
                       run the simulation until it is delivered.
  status  (s)          Show funds, riders and their orders.
  orders  (o)          Show details of all orders.
  riders  (r)          Show every recorded rider status change.
  map     (m)          Show the ASCII map.
  tick [n]  (t)        Advance the simulation by n ticks (default 1).
  save [file] (w)      Save the system state to JSON.
  history (hist)       Show command history.
  !! / !n              Repeat the last command / the n-th history entry.
  help    (h, ?)       Show this help.
  quit    (q) / exit (x)  Leave the program."""

WELCOME_TEXT = "Food Delivery Dispatch Simulator. Type 'help' for commands."


class InputError(ValueError):
    """Raised when user input fails validation."""


class InputManager:
    """Parses commands and dispatches them to the system.

    Attributes:
        system: The SystemManager being controlled.
        command_history: Executed command lines, oldest first.
    """

    def __init__(self, system, input_func=None, output_func=None):
        """Create an input manager.

        Args:
            system: The SystemManager instance.
            input_func: Optional replacement for ``input``.
            output_func: Optional replacement for ``print``.
        """
        self.system = system
        self.command_history = []
        self._input = input_func or input
        self._output = output_func or print
        self._handlers = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "tick": self._cmd_tick,
            "save": self._cmd_save,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
        }

    def run(self):
        """Run the interactive loop until the system stops or input ends."""
        self._output(WELCOME_TEXT)
        while self.system.is_running:
            try:
                line = self._input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self._output("\nExiting.")
                self.system.is_running = False
                break
            self.handle_line(line)

    def handle_line(self, line):
        """Process one command line.

        Args:
            line: Raw text entered by the user.
        """
        text = (line or "").strip()
        if not text:
            return
        if text == "!!":
            if not self.command_history:
                self._output("No command in history.")
                return
            text = self.command_history[-1]
        elif text.startswith("!") and text[1:].isdigit():
            index = int(text[1:])
            if not 1 <= index <= len(self.command_history):
                self._output(f"No history entry {index}.")
                return
            text = self.command_history[index - 1]

        self.command_history.append(text)
        parts = text.split()
        command = COMMAND_ALIASES.get(parts[0].lower(), parts[0].lower())
        handler = self._handlers.get(command)
        if handler is None:
            self._output(f"Unknown command '{parts[0]}'. Type 'help'.")
            return
        try:
            handler(parts[1:])
        except InputError as exc:
            self._output(f"Input error: {exc}")
        except Exception as exc:
            logger.exception("Command '%s' failed", command)
            self._output(f"Error while running '{command}': {exc}")
            fixes = self.system.repair_state()
            if fixes:
                self._output(f"System state recovered ({fixes} fix(es)).")

    @staticmethod
    def parse_coordinates(tokens):
        """Validate four coordinate tokens.

        Args:
            tokens: Sequence of strings: restaurant_x, restaurant_y,
                customer_x, customer_y.

        Returns:
            List of four integers.

        Raises:
            InputError: On wrong count, non-integer or out-of-range values.
        """
        if len(tokens) != 4:
            raise InputError(
                f"expected 4 integers (restaurant x y, customer x y), "
                f"got {len(tokens)}")
        values = []
        names = ["restaurant x", "restaurant y", "customer x", "customer y"]
        for name, token in zip(names, tokens):
            try:
                value = int(token)
            except ValueError as exc:
                raise InputError(
                    f"{name} '{token}' is not an integer") from exc
            if not is_valid_coordinate(value):
                raise InputError(
                    f"{name} {value} is out of range 0-{MAP_SIZE}")
            values.append(value)
        return values

    def _cmd_start(self, args):
        """Handle ``start``: place an order and run it to completion."""
        if args:
            tokens = args
        else:
            tokens = self._input(
                f"Enter restaurant_x restaurant_y customer_x customer_y "
                f"(0-{MAP_SIZE}): ").split()
        rx, ry, cx, cy = self.parse_coordinates(tokens)
        order, added = self.system.submit_order((rx, ry), (cx, cy))

        self._output(f"Order #{order.id} created.")
        self._output(f"Restaurant grid point : ({order.restaurant_x}, "
                     f"{order.restaurant_y})")
        self._output(f"Customer grid point   : ({order.customer_x}, "
                     f"{order.customer_y})")
        self._output(f"New rider added       : {'yes' if added else 'no'}")

        if order.rider_id is None:
            self._output("No rider is available yet; the order is pending.")
            return

        rider = self.system.find_rider(order.rider_id)
        route = self.system.planner.plan_multi(
            rider.position(),
            [Point(order.restaurant_x, order.restaurant_y),
             Point(order.customer_x, order.customer_y)])
        eta = math.ceil(route.total_length / rider.speed) if rider.speed else 0
        self._output(
            f"Assigned rider #{rider.rider_id} | speed {rider.speed} "
            f"units/tick | route {route.total_length:.0f} units | "
            f"estimated {eta} ticks")
        self._output(self.system.display.render_map(
            self.system.riders, self.system.order_manager.orders,
            route.waypoints))

        done = self.system.run_until_order_done(order)
        if done:
            self._output(
                f"Order #{order.id} delivered at tick {order.completion_time}"
                f" (time taken {order.time_taken} ticks, distance "
                f"{order.distance:.1f}, efficiency "
                f"{order.efficiency:.2f} units/tick).")
        else:
            self._output(
                f"Order #{order.id} not delivered within "
                f"{self.system.config.max_ticks_per_order} ticks; use "
                "'status' to monitor progress.")

    def _cmd_status(self, args):
        """Handle ``status``."""
        self._output(self.system.display.format_status(self.system))

    def _cmd_orders(self, args):
        """Handle ``orders``."""
        self._output(self.system.display.format_orders(
            self.system.order_manager.orders))

    def _cmd_riders(self, args):
        """Handle ``riders``."""
        self._output(self.system.display.format_rider_log(
            self.system.riders))

    def _cmd_map(self, args):
        """Handle ``map``."""
        self._output(self.system.display.render_map(
            self.system.riders, self.system.order_manager.orders))

    def _cmd_tick(self, args):
        """Handle ``tick [n]``."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError as exc:
                raise InputError("tick count must be an integer") from exc
            if not 1 <= count <= 10000:
                raise InputError("tick count must be between 1 and 10000")
        for _ in range(count):
            self.system.tick()
        completed = len(self.system.order_manager.completed_orders())
        self._output(f"Advanced {count} tick(s); current tick "
                     f"{self.system.current_tick}, completed orders "
                     f"{completed}.")

    def _cmd_save(self, args):
        """Handle ``save [file]``."""
        path = args[0] if args else "dispatch_state.json"
        if self.system.save_state(path):
            self._output(f"State saved to {path}.")
        else:
            self._output(f"Could not save state to {path}.")

    def _cmd_history(self, args):
        """Handle ``history``."""
        if not self.command_history:
            self._output("History is empty.")
            return
        for index, entry in enumerate(self.command_history, start=1):
            self._output(f"{index:>4}  {entry}")

    def _cmd_help(self, args):
        """Handle ``help``."""
        self._output(HELP_TEXT)

    def _cmd_quit(self, args):
        """Handle ``quit`` and ``exit``."""
        self.system.is_running = False
        self._output("Goodbye.")
