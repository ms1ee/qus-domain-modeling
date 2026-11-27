"""Command-line parsing, validation and command dispatch."""

import logging

from globalvar import get_value
from order_model import COORD_MAX, COORD_MIN
from persistence import save_state
from rider import STATE_NAMES

try:  # Command history and line editing where available.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

logger = logging.getLogger(__name__)

DEFAULT_SAVE_PATH = "dispatch_state.json"

WELCOME = (
    "Food Delivery Dispatch Simulator\n"
    "Type 'help' for commands. Shortcuts: s=start st=status o=orders "
    "r=riders m=map t=tick h=help q=quit"
)

HELP_TEXT = """Commands:
  start [rx ry cx cy]  (s)   Submit an order: restaurant then customer (0-800)
  status               (st)  Show funds, riders, states and order lists
  orders               (o)   Show all orders with distance and time taken
  riders               (r)   Show every rider status change log
  map                  (m)   Show the ASCII map with riders and orders
  tick [n]             (t)   Advance the simulation by n ticks (default 1)
  save [path]                Save system state to JSON
  history                    Show command history
  help                 (h)   Show this help
  quit / exit          (q)   Leave the program"""

COMMANDS = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "save": "save",
    "history": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}


class InputManager:
    """Parses user commands and dispatches them to the system and display."""

    def __init__(self, system, display, input_func=input, output_func=print) -> None:
        """Create the input manager.

        Args:
            system: SystemManager instance.
            display: DisplayManager instance.
            input_func: Callable used to read a line (injectable for tests).
            output_func: Callable used to print output.
        """
        self.system = system
        self.display = display
        self._input = input_func
        self._print = output_func
        self.history = []
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
        }

    @staticmethod
    def parse_command(line: str):
        """Split a raw input line into a canonical command and arguments.

        Args:
            line: Raw user input.

        Returns:
            Tuple (command, args). Command is an empty string for blank input
            and the lowercased token for unknown commands.
        """
        tokens = line.strip().split()
        if not tokens:
            return "", []
        word = tokens[0].lower()
        return COMMANDS.get(word, word), tokens[1:]

    @staticmethod
    def parse_coordinates(tokens) -> list:
        """Validate four integer coordinates in the range 0-800.

        Args:
            tokens: Sequence of string tokens.

        Returns:
            List of four integers [rx, ry, cx, cy].

        Raises:
            ValueError: If the count, type or range is invalid.
        """
        if len(tokens) != 4:
            raise ValueError(
                "expected 4 integers: restaurant_x restaurant_y customer_x customer_y"
            )
        values = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise ValueError(f"'{token}' is not an integer")
            if not COORD_MIN <= value <= COORD_MAX:
                raise ValueError(
                    f"coordinate {value} is out of range {COORD_MIN}-{COORD_MAX}"
                )
            values.append(value)
        return values

    def run(self) -> None:
        """Run the interactive main loop until the system stops."""
        self._print(WELCOME)
        while self.system.running:
            try:
                line = self._input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self._print("\nExiting.")
                break
            if not line or not line.strip():
                continue
            self.history.append(line.strip())
            try:
                self.execute(line)
            except Exception as exc:  # error recovery: keep the session alive
                logger.exception("Command failed: %s", line)
                self._print(f"Error: {exc}. Please try again.")
        self.system.shutdown()

    def execute(self, line: str) -> None:
        """Execute a single command line.

        Args:
            line: Raw user input.
        """
        command, args = self.parse_command(line)
        if not command:
            return
        handler = self._handlers.get(command)
        if handler is None:
            self._print(f"Unknown command '{command}'. Type 'help' for options.")
            return
        handler(args)

    def _cmd_start(self, args) -> None:
        """Handle the start command (order input)."""
        tokens = list(args)
        if not tokens:
            self._print("Enter: restaurant_x restaurant_y customer_x customer_y")
            tokens = self._input("order> ").split()
        try:
            values = self.parse_coordinates(tokens)
        except ValueError as exc:
            self._print(f"Invalid input: {exc}")
            return

        res = (values[0], values[1])
        cus = (values[2], values[3])
        try:
            result = self.system.submit_order(res, cus)
        except ValueError as exc:
            self._print(f"Invalid order: {exc}")
            return

        order = result["order"]
        self._print(f"Order #{order.id} created at tick {order.start_tick}.")
        self._print(f"  Restaurant input {res} -> grid center {order.res_pos}")
        self._print(f"  Customer input {cus} -> grid center {order.cus_pos}")
        if result["new_riders"]:
            ids = ", ".join(f"#{r.rider_id}" for r in result["new_riders"])
            self._print(
                f"  New rider added: {ids} (funds now {self.system.funds})"
            )
        else:
            self._print("  No new rider added.")

        rider = result["rider"]
        if rider is None:
            self._print("  No rider available; the order remains pending.")
            return

        self._print(
            f"  Assigned to rider #{rider.rider_id} "
            f"(speed {rider.speed} units/tick)"
        )
        self._print(
            f"  Route distance {result['distance']} units, "
            f"estimated time {result['eta']} ticks"
        )
        self._print("  Route: " + self.display.format_route(result["route"]))
        self._print(
            self.display.render_map(
                get_value("riders") or [], [order], route=result["route"]
            )
        )

    def _cmd_status(self, args) -> None:
        """Handle the status command."""
        self._print(self.display.format_status(self.system))

    def _cmd_orders(self, args) -> None:
        """Handle the orders command."""
        self._print(self.display.format_orders(get_value("orders") or []))

    def _cmd_riders(self, args) -> None:
        """Handle the riders command."""
        self._print(self.display.format_rider_log(get_value("riders") or []))

    def _cmd_map(self, args) -> None:
        """Handle the map command."""
        self._print(
            self.display.render_map(
                get_value("riders") or [], get_value("orders") or []
            )
        )

    def _cmd_tick(self, args) -> None:
        """Handle the tick command: advance the simulation."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                self._print(f"'{args[0]}' is not an integer")
                return
            if count < 1:
                self._print("Tick count must be at least 1")
                return
        completed = self.system.advance(count)
        self._print(
            f"Advanced {count} tick(s). Current tick: {self.system.tick_count}. "
            f"Orders completed: {completed}."
        )

    def _cmd_save(self, args) -> None:
        """Handle the save command."""
        path = args[0] if args else DEFAULT_SAVE_PATH
        try:
            save_state(path, self.system)
        except OSError as exc:
            self._print(f"Could not save to {path}: {exc}")
            return
        self._print(f"State saved to {path}")

    def _cmd_history(self, args) -> None:
        """Handle the history command."""
        if not self.history:
            self._print("No commands yet.")
            return
        for index, entry in enumerate(self.history, start=1):
            self._print(f"{index:>4}  {entry}")

    def _cmd_help(self, args) -> None:
        """Handle the help command."""
        self._print(HELP_TEXT)

    def _cmd_quit(self, args) -> None:
        """Handle the quit/exit command."""
        self.system.shutdown()
        self._print("Goodbye.")
