"""Command-line entry point for the Food Delivery Order Dispatch simulator.

Run with::

    python src/main.py

Commands:
    start [rx ry cx cy]  create an order (prompts if no coordinates given)
    status               show funds and every rider's state and orders
    orders               show the order table
    riders               show every rider's status-change log
    map                  show the ASCII map
    tick [n]             advance the simulation by n ticks (default 1)
    save [path]          save a JSON snapshot of the state
    help                 show this help
    quit | exit          leave the program
"""

import logging
import sys

import display as display_module
import globalvar
import persistence
import system
from input_manager import InputManager
from order import OrderManager

logger = logging.getLogger("dispatch")

HELP_TEXT = __doc__


def _enable_history():
    """Enable line editing and arrow-key history when readline is available."""
    try:
        import readline  # noqa: F401  (imported for its side effects)
    except ImportError:
        logger.debug("readline not available; history shortcuts still work")


class DispatchApp:
    """Interactive application that routes commands to the managers."""

    def __init__(self, input_manager=None):
        """Create the application and bind the command handlers.

        Args:
            input_manager: Optional :class:`InputManager` (injectable).
        """
        self.inputs = input_manager or InputManager()
        self.orders = OrderManager()
        self.display = display_module.DisplayManager()
        self.system = globalvar.get_value("system")
        self.handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "save": self.cmd_save,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }

    def run(self):
        """Run the main command loop until the running flag is cleared."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while globalvar.get_value("running"):
            try:
                line = self.inputs.read_line("dispatch> ")
            except ValueError as exc:
                print(f"Error: {exc}")
                continue
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            command, args = InputManager.parse_command(line)
            handler = self.handlers.get(command)
            if handler is None:
                print(f"Unknown command: {command!r}. Type 'help' for a list.")
                continue
            try:
                handler(args)
            except ValueError as exc:
                print(f"Input error: {exc}")
            except Exception:
                logger.exception("Unexpected error while running %r", command)
                print("An unexpected error occurred; the system state was preserved.")
        print("Goodbye.")

    def cmd_start(self, args):
        """Create an order and dispatch it to a rider, showing the route."""
        coords = self.inputs.collect_coordinates(args)
        order = self.orders.create_order(*coords)
        rider, new_rider = self.orders.dispatch(order)
        print(f"Order #{order.id}: restaurant cell center {order.res_pos}, "
              f"customer cell center {order.cus_pos}")
        if new_rider:
            print(f"New rider recruited (#{rider.rider_id if rider else '?'}). "
                  f"System funds: {self.system.funds}")
        if rider is None:
            print("No rider is available; the order is pending and will be retried on each tick.")
            return
        print(self.display.render_route(rider, order))

    def cmd_status(self, args):
        """Show the system snapshot."""
        print(self.display.format_status(self.system.funds, self.system.riders,
                                         self.system.tick_count))

    def cmd_orders(self, args):
        """Show the order table."""
        print(self.display.format_orders(self.orders.all_orders()))

    def cmd_riders(self, args):
        """Show the status-change log for every rider."""
        print(self.display.format_rider_logs(self.system.riders))

    def cmd_map(self, args):
        """Show the ASCII map with riders and active orders."""
        print(self.display.render_map(self.system.riders, self.orders.all_orders()))

    def cmd_tick(self, args):
        """Advance the simulation clock by one or more ticks."""
        count = 1
        if args:
            count = InputManager.parse_int(args[0], "tick count")
        if not 1 <= count <= 1000:
            raise ValueError("tick count must be between 1 and 1000")
        before = len(self.orders.completed_orders())
        for _ in range(count):
            self.system.tick()
            self.orders.retry_pending()
            for issue in self.system.check_consistency():
                logger.warning("Consistency repair: %s", issue)
        after = len(self.orders.completed_orders())
        print(f"Tick is now {self.system.tick_count}. Orders completed in this step: "
              f"{after - before}. Pending orders: {len(self.orders.pending_orders())}.")

    def cmd_save(self, args):
        """Save the simulation state to a JSON file."""
        path = args[0] if args else persistence.DEFAULT_STATE_PATH
        try:
            persistence.save_state(path)
        except OSError as exc:
            print(f"Could not save state: {exc}")
            return
        print(f"State saved to {path}")

    def cmd_help(self, args):
        """Print the command reference."""
        print(HELP_TEXT)

    def cmd_quit(self, args):
        """Stop the main loop."""
        globalvar.set_value("running", False)


def main():
    """Program entry point: configure logging, initialise and run the app."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _enable_history()
    config = persistence.load_config()
    system.apply_config(config)
    system.init_system()
    DispatchApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
