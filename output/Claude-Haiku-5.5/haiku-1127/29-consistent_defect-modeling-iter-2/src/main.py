"""Command-line entry point for the Food Delivery Order Dispatch System.

Each iteration of the main loop processes one command and then advances the
simulation by one tick (one unit of time).
"""

import logging
import sys

import globalvar
from display import DisplayManager
from input_manager import InputManager
from system import init_system

logger = logging.getLogger("dispatch")

DEFAULT_SAVE_PATH = "dispatch_state.json"

HELP_TEXT = """Commands:
  start [rx ry cx cy]  (s)  Submit an order (restaurant then customer, 0-1000)
  status               (st) Show funds, riders and their orders
  orders               (o)  Show all orders
  riders               (r)  Show rider event history
  map                  (m)  Show the ASCII map
  wait [n]             (w)  Advance n extra ticks (default 1)
  save [path]          Save state to JSON (default dispatch_state.json)
  history              Show command history
  !!                   Repeat the previous command
  help                 (h)  Show this help
  quit                 (q)  Exit (also: exit)"""


class DispatchApp:
    """Interactive application controller."""

    def __init__(self, system, display, inp, out=print):
        """Create the application.

        Args:
            system: The :class:`SystemManager`.
            display: The :class:`DisplayManager`.
            inp: The :class:`InputManager`.
            out: Callable used for output (defaults to ``print``).
        """
        self.system = system
        self.display = display
        self.inp = inp
        self.out = out

    def run(self):
        """Run the main loop until quit or end of input."""
        self.out("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while globalvar.get_value("running"):
            try:
                line = self.inp.read_line()
            except (EOFError, KeyboardInterrupt):
                self.out("")
                break
            try:
                keep_running = self.handle(line)
            except ValueError as exc:
                self.out(f"Error: {exc}")
                keep_running = True
            except Exception:  # pylint: disable=broad-except
                logger.exception("Unexpected error handling command")
                self.out("Internal error occurred; the system has recovered.")
                keep_running = True
            if not keep_running:
                break
            self.system.advance_tick()
        self.out("Goodbye.")

    def handle(self, line):
        """Process one command line.

        Returns:
            False when the program should exit, otherwise True.
        """
        command, args = self.inp.parse_command(line)
        if command == "":
            return True
        self.inp.record(line.strip())
        handler = getattr(self, f"_cmd_{command}")
        result = handler(args)
        return result is not False

    def _cmd_start(self, args):
        """Handle the ``start`` order command."""
        rx, ry, cx, cy = self.inp.request_order_coordinates(args)
        order, rider, recruited = self.system.submit_order(rx, ry, cx, cy)
        self.out(f"Order {order.order_id} created.")
        self.out(f"Restaurant grid point: {order.res_pos}")
        self.out(f"Customer grid point: {order.cus_pos}")
        self.out(f"New rider recruited: {'yes' if recruited else 'no'}")
        if rider is None:
            self.out("No rider available; the order remains pending until "
                     "a rider can be recruited (funds >= 300).")
            return
        route = self.system.path_planner.plan_route(
            (rider.x, rider.y), [order.res_pos, order.cus_pos])
        length = self.system.path_planner.route_length(route)
        ticks = self.system.path_planner.estimate_ticks(length, rider.speed)
        self.out(self.display.render_route(
            rider, order, route, length, rider.speed, ticks))

    def _cmd_status(self, args):
        """Handle the ``status`` command."""
        issues = self.system.check_consistency()
        self.out(self.display.render_status(self.system, issues))

    def _cmd_orders(self, args):
        """Handle the ``orders`` command."""
        self.out(self.display.render_orders(self.system.order_manager.orders))

    def _cmd_riders(self, args):
        """Handle the ``riders`` command."""
        self.out(self.display.render_rider_log(self.system.riders))

    def _cmd_map(self, args):
        """Handle the ``map`` command."""
        active = self.system.order_manager.active_orders()
        self.out(self.display.render_map(self.system.riders, active))

    def _cmd_wait(self, args):
        """Handle the ``wait`` command, advancing extra ticks."""
        count = self.inp.parse_count(args)
        for _ in range(count):
            self.system.advance_tick()
        self.out(f"Advanced {count} tick(s); current tick {self.system.tick}.")

    def _cmd_save(self, args):
        """Handle the ``save`` command."""
        path = args[0] if args else DEFAULT_SAVE_PATH
        try:
            self.system.save_state(path)
        except OSError as exc:
            self.out(f"Could not save state: {exc}")
            return
        self.out(f"State saved to {path}.")

    def _cmd_history(self, args):
        """Handle the ``history`` command."""
        if not self.inp.command_history:
            self.out("No history yet.")
            return
        for index, entry in enumerate(self.inp.command_history, start=1):
            self.out(f"  {index:>3}: {entry}")

    def _cmd_help(self, args):
        """Handle the ``help`` command."""
        self.out(HELP_TEXT)

    def _cmd_quit(self, args):
        """Handle the ``quit`` command."""
        globalvar.set_value("running", False)
        return False


def main(argv=None):
    """Program entry point.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).
            Supported flags: ``--debug`` and ``--config PATH``.

    Returns:
        Process exit code.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    level = logging.DEBUG if "--debug" in argv else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config_path = None
    if "--config" in argv:
        index = argv.index("--config")
        if index + 1 < len(argv):
            config_path = argv[index + 1]

    system = init_system(config_path)
    app = DispatchApp(system, DisplayManager(), InputManager())
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
