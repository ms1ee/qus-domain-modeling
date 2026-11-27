"""Command-line entry point for the Food Delivery Order Dispatch simulator."""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:  # Enables line editing and history on platforms that provide readline.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    pass

from display_manager import DisplayManager  # noqa: E402
from input_manager import InputError, InputManager  # noqa: E402
from order_model import STATUS_COMPLETED  # noqa: E402
from system import MAX_TICKS_PER_COMMAND, SystemManager, init_system  # noqa: E402
import globalvar  # noqa: E402
from rider import Rider  # noqa: E402
from order_model import Order  # noqa: E402

logger = logging.getLogger("dispatch")

MAX_TRIP_TICKS = 2000
DEFAULT_SAVE_PATH = "dispatch_state.json"

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy]  (s) Create an order: restaurant x/y then customer x/y (0-800).
                           Runs the simulation until the order is delivered and
                           shows the route map.
  status               (t) Funds, rider count and each rider's state and orders.
  orders               (o) Details of all orders.
  riders               (r) Status-change log for every rider.
  map                  (m) ASCII map with riders, restaurants and customers.
  tick [n]             (k) Advance the simulation by n ticks (default 1).
  save [path]          (v) Save state to a JSON file.
  history              (y) Show recent commands.
  help                 (h, ?) Show this help.
  quit / exit          (q) Leave the program."""


def simulate_until_delivered(
    system: SystemManager, order: Order, rider: Rider
) -> Tuple_List:
    """Advance the simulation until the order is delivered.

    Args:
        system: The SystemManager driving the simulation.
        order: Order being tracked.
        rider: Rider expected to serve the order (its positions are traced).

    Returns:
        Tuple ``(trail, ticks)`` where ``trail`` lists the rider's positions
        from the start of the trip and ``ticks`` is the number of ticks run.
    """
    trail = [(rider.x, rider.y)]
    ticks = 0
    while order.status != STATUS_COMPLETED and ticks < MAX_TRIP_TICKS:
        system.tick()
        ticks += 1
        trail.append((rider.x, rider.y))
    return trail, ticks


class App:
    """Interactive command loop tying together input, system and display."""

    def __init__(self, reader=None, writer=print) -> None:
        """Initialise the system and the UI helpers.

        Args:
            reader: Optional line reader (defaults to ``input``).
            writer: Output callable (defaults to ``print``).
        """
        self.system = init_system()
        self.display = DisplayManager()
        self.inp = InputManager(reader)
        self.out = writer
        self.handlers = {
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

    # ----------------------------------------------------------- main loop
    def run(self) -> None:
        """Run the interactive loop until quit, EOF or interrupt."""
        self.out("Food Delivery Order Dispatch System (8x8 grid, 800x800 units)")
        self.out("Type 'help' for the command list.")
        while self.system.running:
            try:
                line = self.inp.read_line("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self.out("")
                break
            name, args = InputManager.parse_command(line)
            if not name:
                continue
            handler = self.handlers.get(name)
            if handler is None:
                self.out(f"Unknown command '{name}'. Type 'help' for the command list.")
                continue
            try:
                handler(args)
            except (EOFError, KeyboardInterrupt):
                self.out("")
                break
            except InputError as exc:
                self.out(f"Input error: {exc}")
            except Exception:  # Error recovery: keep the simulation running.
                logger.exception("Command '%s' failed", name)
                self.out("An unexpected error occurred; the system state was kept. See log.")
        self.system.stop()
        self.out("Goodbye.")

    # ------------------------------------------------------------ helpers
    def _prompt_coordinates(self):
        """Prompt until valid coordinates or a blank line (cancel) is entered."""
        while True:
            text = self.inp.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y (blank to cancel): "
            )
            if not text:
                return None
            try:
                return InputManager.parse_coordinates([text])
            except InputError as exc:
                self.out(f"Input error: {exc}. Try again.")

    # ----------------------------------------------------------- commands
    def cmd_start(self, args) -> None:
        """Create an order, dispatch it and simulate it to completion."""
        if args:
            coords = InputManager.parse_coordinates(args)
        else:
            coords = self._prompt_coordinates()
            if coords is None:
                self.out("Order cancelled.")
                return
        res_pos = [coords[0], coords[1]]
        cus_pos = [coords[2], coords[3]]
        result = self.system.submit_order(res_pos, cus_pos)
        order = result["order"]
        rider = result["rider"]
        if rider is None:
            self.out(
                f"Order #{order.id} is pending: no rider is available "
                f"(funds {self.system.funds}, recruit needs >= "
                f"{self.system.config['recruit_min_funds']})."
            )
            return
        trail, ticks = simulate_until_delivered(self.system, order, rider)
        self.out(self.display.render_route(order, rider, trail, ticks, result["new_rider"]))
        if order.status != STATUS_COMPLETED:
            self.out(f"Order #{order.id} is not yet delivered after {ticks} ticks.")

    def cmd_status(self, args) -> None:
        """Show funds, riders and any consistency problems."""
        self.out(self.display.render_status(self.system))
        problems = self.system.check_consistency()
        for problem in problems:
            self.out(f"WARNING: {problem}")

    def cmd_orders(self, args) -> None:
        """Show the order table."""
        self.out(self.display.render_orders(self.system.order_manager.all_orders()))

    def cmd_riders(self, args) -> None:
        """Show the status-change log of all riders."""
        self.out(self.display.render_rider_log(self.system.riders))

    def cmd_map(self, args) -> None:
        """Show the ASCII map with riders and active orders."""
        self.out(
            self.display.render_map(self.system.riders, self.system.order_manager.all_orders())
        )

    def cmd_tick(self, args) -> None:
        """Advance the simulation by one or more ticks."""
        count = InputManager.parse_positive_int(args, 1, MAX_TICKS_PER_COMMAND)
        for _ in range(count):
            self.system.tick()
        self.out(f"Advanced {count} tick(s); time is now {self.system.time}.")

    def cmd_save(self, args) -> None:
        """Save the system state to a JSON file."""
        path = args[0] if args else DEFAULT_SAVE_PATH
        try:
            self.system.save_state(path)
        except OSError as exc:
            self.out(f"Could not save state to {path}: {exc}")
            return
        self.out(f"State saved to {path}.")

    def cmd_history(self, args) -> None:
        """Print the recent command history."""
        if not self.inp.history:
            self.out("(no history)")
            return
        for index, entry in enumerate(self.inp.history, start=1):
            self.out(f"{index:>4}  {entry}")

    def cmd_help(self, args) -> None:
        """Print the command help text."""
        self.out(HELP_TEXT)

    def cmd_quit(self, args) -> None:
        """Stop the main loop."""
        self.system.stop()


Tuple_List = list


def main(argv=None) -> int:
    """Program entry point.

    Args:
        argv: Optional argument list; ``--debug`` enables debug logging.

    Returns:
        Process exit code.
    """
    argv = sys.argv[1:] if argv is None else argv
    level = logging.DEBUG if "--debug" in argv else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
