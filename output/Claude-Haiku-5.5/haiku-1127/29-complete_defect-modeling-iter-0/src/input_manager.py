"""Command-line interaction: parsing, dispatch, shortcuts and history.

Commands:
    start [rx ry cx cy]  create an order and assign the closest rider
    status               funds, tick, riders and their states
    orders               all orders with details
    riders               status-change history of all riders
    map                  ASCII map of riders and active orders
    tick [n]             advance the simulation by n ticks (default 1)
    save                 write the state file
    history              list previous commands
    help                 show command help
    quit / exit          save and exit
Shortcuts: s, st, o, r, m, t, sv, hist, h, ?, q, x; ``!!`` repeats the last
command and ``!n`` repeats command number n from ``history``.
"""

import logging
import re

from display import DisplayManager
from path_planner import PathPlanner, Route, cell_of
from order_model import MAP_SIZE

try:  # readline gives line editing and arrow-key history where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows fallback
    readline = None

logger = logging.getLogger(__name__)

MAX_TICKS_PER_COMMAND = 10000

HELP_TEXT = """Commands:
  start [rx ry cx cy]  create an order (restaurant then customer, 0-800)
  status               show funds, tick, riders and their states
  orders               list all orders with details
  riders               list every rider status change
  map                  show the ASCII map
  tick [n]             advance the simulation by n ticks (default 1)
  save                 save the state file
  history              show command history
  help                 show this help
  quit | exit          save and exit
Shortcuts: s=start st=status o=orders r=riders m=map t=tick sv=save
           hist=history h/?=help q/x=quit  !!=repeat last  !n=repeat #n"""


def parse_coordinates(text):
    """Parse four integer coordinates from text.

    Accepts values separated by spaces and/or commas.

    Args:
        text: Input text such as ``"100 200 700 600"``.

    Returns:
        List of four integers ``[rx, ry, cx, cy]``.

    Raises:
        ValueError: On wrong count, non-integer tokens or out-of-range values.
    """
    parts = [p for p in re.split(r"[\s,]+", text.strip()) if p]
    if len(parts) != 4:
        raise ValueError(
            "expected 4 integers: restaurant_x restaurant_y customer_x customer_y"
        )
    values = []
    for part in parts:
        try:
            value = int(part)
        except ValueError:
            raise ValueError(f"'{part}' is not an integer") from None
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"coordinate {value} is out of range 0-{MAP_SIZE}")
        values.append(value)
    return values


class InputManager:
    """Reads, validates and dispatches user commands.

    Attributes:
        system: The SystemManager controlling the simulation.
        display: DisplayManager used for output formatting.
        command_history: Executed command lines in order.
    """

    ALIASES = {
        "s": "start",
        "st": "status",
        "o": "orders",
        "r": "riders",
        "m": "map",
        "t": "tick",
        "sv": "save",
        "hist": "history",
        "h": "help",
        "?": "help",
        "q": "quit",
        "x": "exit",
    }

    def __init__(self, system_manager, display=None, input_func=None, output_func=None):
        """Create the input manager.

        Args:
            system_manager: SystemManager instance.
            display: Optional DisplayManager.
            input_func: Optional replacement for ``input``.
            output_func: Optional replacement for ``print``.
        """
        self.system = system_manager
        self.display = display or DisplayManager()
        self.command_history = []
        self._input = input_func or input
        self._output = output_func or print
        self._planner = PathPlanner()
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
        """Run the interactive loop until the system stops."""
        self._print("Food Delivery Order Dispatch System. Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = self._input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self._print("")
                self._cmd_quit([])
                break
            self.handle_line(line)
        self.system.shutdown()
        self._print("Goodbye.")

    def handle_line(self, line):
        """Process one raw input line.

        Errors are reported to the user and never terminate the loop.

        Args:
            line: Raw text entered by the user.
        """
        text = (line or "").strip()
        if not text:
            return
        if text.startswith("!"):
            text = self._resolve_history(text)
            if text is None:
                return
        self.command_history.append(text)
        if readline is not None:  # pragma: no cover - interactive only
            try:
                readline.add_history(text)
            except Exception:
                logger.debug("readline history unavailable")
        try:
            self.execute(text)
        except Exception:
            logger.exception("Unexpected error while executing '%s'", text)
            self._print("Unexpected error: the command failed, system state preserved.")

    def execute(self, text):
        """Dispatch a command line to its handler.

        Args:
            text: Command line (already stripped and history-resolved).
        """
        parts = text.split()
        name = parts[0].lower()
        args = parts[1:]
        name = self.ALIASES.get(name, name)
        handler = self._handlers.get(name)
        if handler is None:
            self._print(f"Unknown command '{parts[0]}'. Type 'help' for a list of commands.")
            return
        handler(args)

    def _resolve_history(self, text):
        """Resolve ``!!`` or ``!n`` to a previous command line."""
        if text == "!!":
            if not self.command_history:
                self._print("No previous command to repeat.")
                return None
            return self.command_history[-1]
        match = re.fullmatch(r"!(\d+)", text)
        if not match:
            self._print("Invalid history reference. Use !! or !<number>.")
            return None
        index = int(match.group(1))
        if not 1 <= index <= len(self.command_history):
            self._print(f"No command #{index} in history.")
            return None
        return self.command_history[index - 1]

    def _print(self, message):
        """Write a message through the output function."""
        self._output(message)

    def _cmd_start(self, args):
        """Create an order from four coordinates and assign a rider."""
        if args:
            text = " ".join(args)
        else:
            try:
                text = self._input(
                    "Enter restaurant x y and customer x y (0-800), e.g. 100 200 700 600: "
                )
            except EOFError:
                self._print("Input cancelled.")
                return
        try:
            rx, ry, cx, cy = parse_coordinates(text)
            order = self.system.order_manager.create_order((rx, ry), (cx, cy))
        except (TypeError, ValueError) as exc:
            self._print(f"Input error: {exc}")
            return

        new_rider = self.system.check_recruitment()
        rider = self.system.order_manager.assign_order(order)

        restaurant_cell = cell_of(order.restaurant_x, order.restaurant_y)
        customer_cell = cell_of(order.customer_x, order.customer_y)
        self._print(f"Order #{order.id} created at tick {order.start_time}.")
        self._print(
            f"  Restaurant: input ({rx}, {ry}) -> cell {restaurant_cell}, "
            f"center ({order.restaurant_x}, {order.restaurant_y})"
        )
        self._print(
            f"  Customer:   input ({cx}, {cy}) -> cell {customer_cell}, "
            f"center ({order.customer_x}, {order.customer_y})"
        )
        if new_rider:
            self._print(f"  New rider added: yes (rider #{self.system.rider_id_counter})")
        else:
            self._print("  New rider added: no")

        if rider is None:
            self._print("  No rider available; the order is queued as pending.")
            return

        self._print(f"  Assigned to rider #{rider.rider_id} (speed {rider.speed} units/tick).")
        leg1 = self._planner.plan_route(cell_of(rider.x, rider.y), restaurant_cell)
        leg2 = self._planner.plan_route(restaurant_cell, customer_cell)
        route = Route(
            leg1.waypoints + leg2.waypoints[1:],
            leg1.total_distance + leg2.total_distance,
        )
        self._print(self.display.render_map(self.system.riders, self.system.order_manager.active_orders(), route))
        self._print(self.display.render_route_summary(route, rider.speed))

    def _cmd_status(self, args):
        """Print the system status snapshot."""
        self._print(
            self.display.render_status(
                self.system.current_tick,
                self.system.funds,
                self.system.riders,
                len(self.system.order_manager.pending),
            )
        )

    def _cmd_orders(self, args):
        """Print the table of all orders."""
        self._print(self.display.render_orders(self.system.order_manager.orders))

    def _cmd_riders(self, args):
        """Print the status-change history of all riders."""
        self._print(self.display.render_rider_log(self.system.riders))

    def _cmd_map(self, args):
        """Print the ASCII map of riders and active orders."""
        self._print(
            self.display.render_map(self.system.riders, self.system.order_manager.active_orders())
        )

    def _cmd_tick(self, args):
        """Advance the simulation by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                self._print("Input error: tick count must be an integer.")
                return
        if not 1 <= count <= MAX_TICKS_PER_COMMAND:
            self._print(f"Input error: tick count must be between 1 and {MAX_TICKS_PER_COMMAND}.")
            return
        completed = 0
        for _ in range(count):
            completed += self.system.tick()
        self._print(
            f"Advanced {count} tick(s). Current tick: {self.system.current_tick}. "
            f"Orders delivered: {completed}."
        )

    def _cmd_save(self, args):
        """Persist the state to the configured state file."""
        try:
            path = self.system.save_state()
            self._print(f"State saved to {path}.")
        except OSError as exc:
            self._print(f"Could not save state: {exc}")

    def _cmd_history(self, args):
        """List previously entered commands."""
        if not self.command_history:
            self._print("History is empty.")
            return
        for number, command in enumerate(self.command_history, start=1):
            self._print(f"  {number:>3}  {command}")

    def _cmd_help(self, args):
        """Print command help."""
        self._print(HELP_TEXT)

    def _cmd_quit(self, args):
        """Stop the main loop; state is saved on shutdown."""
        self.system.is_running = False
