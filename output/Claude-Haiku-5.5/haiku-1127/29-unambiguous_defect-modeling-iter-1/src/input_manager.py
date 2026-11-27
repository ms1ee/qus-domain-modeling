"""Command parsing, validation and the interactive command loop."""

import logging
import re

import config
import globalvar
import grid_map
import persistence
from display import DisplayManager
from order import OrderManager
from system import SystemManager

try:  # Enables line editing and up/down history on supported platforms.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows without pyreadline
    pass

logger = logging.getLogger(__name__)

PROMPT = "dispatch> "
COORD_SPLIT = re.compile(r"[\s,]+")

COMMAND_ALIASES = {
    "s": "start",
    "t": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "n": "step",
    "w": "save",
    "l": "load",
    "y": "history",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
}

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy]  [s] Create an order. Restaurant then customer coordinates
                       (integers 0-800). Prompts if no arguments are given.
  status               [t] Fund balance, tick, and every rider's state and orders.
  orders               [o] Details of all orders.
  riders [id]          [r] Status-change log for all riders (or one rider).
  map                  [m] ASCII map with riders and active orders.
  step [n]             [n] Advance the simulation by n ticks (default 1).
  save [file]          [w] Save state to JSON.
  load [file]          [l] Load state from JSON.
  history              [y] Show recent commands.
  help                 [h] Show this help.
  quit / exit          [q] [x] Exit the program."""


class InputManager:
    """Parses user commands and dispatches them to the managers."""

    def __init__(self, system, order_manager, display, input_func=input, output_func=print):
        """Create the input manager.

        Args:
            system: SystemManager facade.
            order_manager: OrderManager used for order creation and assignment.
            display: DisplayManager used for output rendering.
            input_func: Callable used to read a line (injectable for tests).
            output_func: Callable used to print output.
        """
        self.system = system
        self.order_manager = order_manager
        self.display = display
        self.input_func = input_func
        self.output_func = output_func
        self.command_history = []
        self._handlers = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "step": self._cmd_step,
            "save": self._cmd_save,
            "load": self._cmd_load,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
        }

    def _print(self, text=""):
        """Print text through the output callable."""
        self.output_func(text)

    @staticmethod
    def parse_coordinates(tokens):
        """Validate and convert four coordinate tokens.

        Args:
            tokens: Sequence of four string tokens.

        Returns:
            List of four integers in the range 0-800.

        Raises:
            ValueError: On wrong count, non-integer or out-of-range values.
        """
        if len(tokens) != 4:
            raise ValueError(
                "Expected 4 coordinates: restaurant_x restaurant_y "
                "customer_x customer_y."
            )
        values = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise ValueError(f"'{token}' is not an integer.") from None
            if not 0 <= value <= config.MAP_SIZE:
                raise ValueError(
                    f"Coordinate {value} is out of range 0-{config.MAP_SIZE}."
                )
            values.append(value)
        return values

    def handle_command(self, line):
        """Parse and execute a single command line.

        Args:
            line: Raw user input.

        Returns:
            True if the program should keep running.
        """
        line = line.strip()
        if not line:
            return self.system.is_running
        self.command_history.append(line)
        parts = line.split()
        name = parts[0].lower()
        name = COMMAND_ALIASES.get(name, name)
        handler = self._handlers.get(name)
        if handler is None:
            self._print(f"Unknown command '{parts[0]}'. Type 'help' for a list of commands.")
            return self.system.is_running
        try:
            handler(parts[1:])
        except ValueError as exc:
            self._print(f"Error: {exc}")
        except RuntimeError as exc:
            self._print(f"Error: {exc}")
        except OSError as exc:
            self._print(f"File error: {exc}")
        except Exception:  # Error recovery: keep the session alive.
            logger.exception("Unexpected error handling command '%s'", line)
            self._print("An unexpected error occurred; the system state is preserved.")
        return self.system.is_running

    def run(self):
        """Run the interactive loop until the system stops."""
        self._print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = self.input_func(PROMPT)
            except (EOFError, KeyboardInterrupt):
                self._print("")
                self.system.stop()
                break
            self.handle_command(line)

    def _cmd_start(self, args):
        """Create and assign an order from inline or prompted coordinates."""
        if args:
            tokens = COORD_SPLIT.split(" ".join(args).strip())
        else:
            raw = self.input_func(
                "Enter restaurant_x restaurant_y customer_x customer_y: "
            )
            tokens = COORD_SPLIT.split(raw.strip())
        rx, ry, cx, cy = self.parse_coordinates([t for t in tokens if t])
        order = self.order_manager.create_order((rx, ry), (cx, cy))
        rider, new_rider = self.order_manager.assign_order(order)

        self._print(f"Order #{order.order_id} created.")
        self._print(
            f"Restaurant grid position: {order.res_pos} (input {(rx, ry)})"
        )
        self._print(
            f"Customer grid position:   {order.cus_pos} (input {(cx, cy)})"
        )
        if new_rider:
            self._print(f"A new rider was recruited: rider {rider.rider_id}.")
        else:
            self._print(f"No new rider added; assigned to rider {rider.rider_id}.")
        self._print(f"Rider {rider.rider_id} has {len(rider.orders)} order(s) queued.")
        self._print(self.display.render_route(rider, order))

    def _cmd_status(self, args):
        """Show the system snapshot."""
        system = self.system
        self._print(
            self.display.render_status(system.funds, system.current_tick, system.riders)
        )

    def _cmd_orders(self, args):
        """Show all orders."""
        self._print(self.display.render_orders(self.order_manager.all_orders()))

    def _cmd_riders(self, args):
        """Show rider status-change logs, optionally for one rider."""
        riders = list(self.system.riders)
        if args:
            try:
                rider_id = int(args[0])
            except ValueError:
                raise ValueError(f"'{args[0]}' is not a valid rider ID.") from None
            riders = [r for r in riders if r.rider_id == rider_id]
            if not riders:
                raise ValueError(f"Rider {rider_id} does not exist.")
        self._print(self.display.render_riders(riders))

    def _cmd_map(self, args):
        """Render the ASCII map."""
        self._print(
            self.display.render_map(
                riders=self.system.riders,
                orders=self.order_manager.active_orders(),
            )
        )

    def _cmd_step(self, args):
        """Advance the simulation by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"'{args[0]}' is not an integer.") from None
            if not 1 <= count <= 1000:
                raise ValueError("Step count must be between 1 and 1000.")
        for _ in range(count):
            self.system.advance_tick()
        busy = sum(1 for r in self.system.riders if r.state != 0)
        self._print(
            f"Advanced {count} tick(s). Now at tick {self.system.current_tick}; "
            f"{busy} rider(s) busy; funds {self.system.funds}."
        )

    def _cmd_save(self, args):
        """Save the state to a JSON file."""
        path = persistence.save_state(args[0] if args else None)
        self._print(f"State saved to {path}.")

    def _cmd_load(self, args):
        """Load state from a JSON file."""
        path = args[0] if args else config.SETTINGS["save_file"]
        try:
            persistence.load_state(path)
        except FileNotFoundError:
            raise ValueError(f"Save file '{path}' not found.") from None
        self._print(f"State loaded from {path}.")

    def _cmd_history(self, args):
        """Show the most recent commands."""
        recent = self.command_history[-20:]
        if not recent:
            self._print("No commands yet.")
            return
        for index, cmd in enumerate(recent, start=max(1, len(self.command_history) - 19)):
            self._print(f"{index:>4}  {cmd}")

    def _cmd_help(self, args):
        """Show the help text."""
        self._print(HELP_TEXT)

    def _cmd_quit(self, args):
        """Stop the main loop."""
        self.system.stop()
        self._print("Goodbye.")


def build_input_manager(input_func=input, output_func=print):
    """Create a fully wired InputManager using the global state.

    Args:
        input_func: Callable used to read input.
        output_func: Callable used to print output.

    Returns:
        Configured InputManager instance.
    """
    system = SystemManager()
    return InputManager(
        system,
        OrderManager(system),
        DisplayManager(),
        input_func=input_func,
        output_func=output_func,
    )
