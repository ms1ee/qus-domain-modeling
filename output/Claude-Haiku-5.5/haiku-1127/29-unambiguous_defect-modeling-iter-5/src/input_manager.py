"""Command parsing, validation and the interactive command loop."""

import logging

try:  # Enables line editing and history keys on supported platforms.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    pass

from path_planner import MAP_SIZE

logger = logging.getLogger(__name__)

SHORTCUTS = {
    "n": "start",
    "s": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "q": "quit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant x/y, customer x/y, 0-800).
                       Prompts for values if omitted.
  status               Show funds, riders and their order lists.
  orders               Show details for all orders.
  riders               Show the status-change log for all riders.
  map                  Show the ASCII map with riders and active orders.
  tick [n]             Advance the simulation by n ticks (default 1).
  save [path]          Save a JSON snapshot (default snapshot.json).
  history              Show command history.
  help                 Show this help.
  quit / exit          Leave the program.
Shortcuts: n=start s=status o=orders r=riders m=map t=tick h=help q=quit
History:   !! repeats the last command, !N repeats command number N."""

COORD_NAMES = ["restaurant x", "restaurant y", "customer x", "customer y"]


class InputManager:
    """Parses user commands and dispatches them to the system.

    Attributes:
        system (SystemManager): The simulation being controlled.
        display (DisplayManager): Renderer for output.
        command_history (list[str]): Previously executed command lines.
    """

    def __init__(self, system, display, input_func=None, output_func=None):
        """Create the input manager.

        Args:
            system: The :class:`SystemManager` instance.
            display: The :class:`DisplayManager` instance.
            input_func: Callable used to read a line (defaults to ``input``).
            output_func: Callable used to print text (defaults to ``print``).
        """
        self.system = system
        self.display = display
        self.command_history = []
        self._input = input_func or input
        self._output = output_func or print
        self._handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "save": self.cmd_save,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    # ------------------------------------------------------------------
    # Parsing and validation
    # ------------------------------------------------------------------
    @staticmethod
    def parse_coordinate_tokens(tokens):
        """Validate four coordinate tokens.

        Args:
            tokens: Sequence of four strings.

        Returns:
            List of four integers in the range 0..800.

        Raises:
            ValueError: If the count, type or range is invalid.
        """
        if len(tokens) != 4:
            raise ValueError("expected four integers: restaurant x y, customer x y")
        values = []
        for name, token in zip(COORD_NAMES, tokens):
            try:
                value = int(token)
            except ValueError:
                raise ValueError(f"{name} must be an integer, got '{token}'")
            if not 0 <= value <= MAP_SIZE:
                raise ValueError(
                    f"{name} must be between 0 and {MAP_SIZE}, got {value}")
            values.append(value)
        return values

    def _prompt_coordinates(self):
        """Interactively ask for the four coordinates.

        Returns:
            List of four integers, or ``None`` if the user cancels.
        """
        values = []
        for name in COORD_NAMES:
            while True:
                raw = self._input(f"{name} (0-{MAP_SIZE}, or 'cancel'): ").strip()
                if raw.lower() == "cancel":
                    return None
                try:
                    values.extend(self.parse_coordinate_tokens(
                        [raw] + ["0"] * (4 - len(values) - 1)
                        if False else [str(self._check_single(name, raw))]
                        + ["0"] * 3))
                    break
                except ValueError as exc:
                    self._output(f"Error: {exc}")
        return values

    @staticmethod
    def _check_single(name, raw):
        """Validate one coordinate string and return its integer value."""
        try:
            value = int(raw)
        except ValueError:
            raise ValueError(f"{name} must be an integer, got '{raw}'")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"{name} must be between 0 and {MAP_SIZE}, got {value}")
        return value

    def _resolve_history(self, line):
        """Expand ``!!`` or ``!N`` into a previous command line.

        Returns:
            The resolved command line, or ``None`` on error.
        """
        if line == "!!":
            if not self.command_history:
                self._output("Error: no previous command.")
                return None
            return self.command_history[-1]
        if line[1:].isdigit():
            index = int(line[1:])
            if 1 <= index <= len(self.command_history):
                return self.command_history[index - 1]
        self._output(f"Error: no history entry for '{line}'.")
        return None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def process(self, line):
        """Execute one command line.

        Args:
            line: Raw user input.

        Returns:
            False if the program should exit, True otherwise.
        """
        line = line.strip()
        if not line:
            return True
        if line.startswith("!"):
            resolved = self._resolve_history(line)
            if resolved is None:
                return True
            line = resolved

        self.command_history.append(line)
        tokens = line.split()
        name = tokens[0].lower()
        command = SHORTCUTS.get(name, name)
        handler = self._handlers.get(command)
        if handler is None:
            self._output(f"Unknown command '{tokens[0]}'. Type 'help' for commands.")
            return True
        try:
            result = handler(tokens[1:])
            return result is not False
        except ValueError as exc:
            self._output(f"Error: {exc}")
        except Exception:  # recovery: keep the session alive
            logger.exception("Unexpected error handling '%s'", line)
            self._output("Unexpected internal error; system state was checked and repaired.")
            self.system.verify_consistency()
        return True

    def run(self):
        """Run the interactive loop until the user quits."""
        self._output("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = self._input("> ")
            except (EOFError, KeyboardInterrupt):
                self._output("")
                break
            if not self.process(line):
                break

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def cmd_start(self, args):
        """Create an order and display the assignment result."""
        if args:
            values = self.parse_coordinate_tokens(args)
        else:
            values = self._prompt_coordinates()
            if values is None:
                self._output("Order cancelled.")
                return
        restaurant = (values[0], values[1])
        customer = (values[2], values[3])
        result = self.system.submit_order(restaurant, customer)
        order = result["order"]
        rx, ry = order.restaurant_pos
        cx, cy = order.customer_pos
        self._output(f"Order #{order.id} created.")
        self._output(f"Restaurant grid point: ({rx}, {ry})")
        self._output(f"Customer grid point:   ({cx}, {cy})")
        if result["new_rider"]:
            rider = result["rider"]
            self._output(f"New rider R{rider.rider_id} was recruited "
                         f"(cost {self.system.rider_recruitment_cost}). "
                         f"Funds: {self.system.funds}")
        else:
            self._output("No new rider was recruited.")
        if not result["assigned"]:
            self._output(f"Order not assigned: {result['reason']}.")
            return
        rider = result["rider"]
        self._output(f"Assigned to rider R{rider.rider_id}: speed {result['speed']} "
                     f"units/tick, estimated time {result['estimated_time']} ticks.")
        self._output(self.display.render_map(
            self.system.riders, self.system.active_orders(), route=result["route"]))

    def cmd_status(self, args):
        """Show the system status snapshot."""
        self._output(self.display.render_status(self.system))

    def cmd_orders(self, args):
        """Show all order details."""
        self._output(self.display.render_orders(self.system.order_manager.orders))

    def cmd_riders(self, args):
        """Show every recorded rider status change in time order."""
        entries = []
        for rider in self.system.riders:
            entries.extend(rider.log)
        if not entries:
            self._output("No rider events recorded.")
            return
        entries.sort(key=lambda e: (e["time"], e["rider_id"]))
        lines = ["Rider event log:"]
        for e in entries:
            order = f"order #{e['order_id']}" if e["order_id"] is not None else "-"
            lines.append(
                f"  t={e['time']:<5} | Rider {e['rider_id']:>3} | "
                f"{e['event']:<20} | {order:<12} | pos ({e['x']}, {e['y']})")
        self._output("\n".join(lines))

    def cmd_map(self, args):
        """Show the ASCII map."""
        self._output(self.display.render_map(self.system.riders,
                                             self.system.active_orders()))

    def cmd_tick(self, args):
        """Advance the simulation clock."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError("tick count must be a positive integer")
            if count <= 0 or count > 10000:
                raise ValueError("tick count must be between 1 and 10000")
        net = self.system.run_ticks(count)
        completed = len(self.system.order_manager.completed_orders())
        self._output(f"Advanced {count} tick(s). Time: {self.system.simulated_time}, "
                     f"net income: {net}, funds: {self.system.funds}, "
                     f"completed orders: {completed}.")

    def cmd_save(self, args):
        """Save a JSON snapshot of the system."""
        path = args[0] if args else "snapshot.json"
        try:
            self.system.save_snapshot(path)
        except OSError as exc:
            raise ValueError(f"could not write '{path}': {exc}")
        self._output(f"Snapshot saved to {path}.")

    def cmd_history(self, args):
        """Print the command history."""
        if not self.command_history:
            self._output("No commands in history.")
            return
        for index, entry in enumerate(self.command_history, start=1):
            self._output(f"  {index:>3}  {entry}")

    def cmd_help(self, args):
        """Print the help text."""
        self._output(HELP_TEXT)

    def cmd_quit(self, args):
        """Stop the program."""
        self.system.stop()
        self._output("Goodbye.")
        return False
