"""Entry point: command-line food delivery dispatch simulator.

Run with ``python src/main.py [config.json]``.
"""

import logging
import math
import sys

from display import DisplayManager
from globalvar import get_value
from input_manager import InputManager
from order import OrderManager
from path_planner import PathPlanner
from rider import STATE_IDLE
from system import SystemManager

logger = logging.getLogger("dispatch")

DEFAULT_CONFIG_PATH = "dispatch_config.json"
DEFAULT_STATE_PATH = "dispatch_state.json"
MAX_TICKS_PER_COMMAND = 1000
BANNER = "Food Delivery Order Dispatch System - type 'help' for commands."


class DispatchApp:
    """Interactive application tying together all system modules."""

    def __init__(self, config_path=None):
        """Create the application and initialise the system state.

        Args:
            config_path: Optional JSON configuration file path.
        """
        self.system = SystemManager(config_path)
        self.orders = OrderManager()
        self.display = DisplayManager()
        self.inputs = InputManager()
        self._handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "tick": self.cmd_tick,
            "map": self.cmd_map,
            "save": self.cmd_save,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }

    def run(self):
        """Run the interactive main loop until the system stops."""
        print(BANNER)
        print(self.display.help_text())
        while get_value("running", True):
            try:
                raw = self.inputs.read_line("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.stop()
                break
            if not raw:
                continue
            try:
                line = self.inputs.expand(raw)
            except ValueError as exc:
                print(f"Error: {exc}")
                continue
            if not line:
                continue
            self.inputs.record(line)
            name, args = self.inputs.parse(line)
            if name is None:
                print(f"Unknown command '{line.split()[0]}'. Type 'help' for the command list.")
                continue
            try:
                self._handlers[name](args)
            except ValueError as exc:
                print(f"Input error: {exc}")
            except Exception as exc:  # keep the simulator alive on unexpected errors
                logger.exception("Unexpected error while running '%s'", line)
                print(f"Unexpected error: {exc}. System state has been preserved.")
            self.check_consistency()

    def check_consistency(self):
        """Verify and repair rider/order state after each command.

        Ensures in-progress riders have an active order, idle riders hold no
        stale order reference, and completed orders are not still queued.
        """
        for rider in self.system.riders:
            if rider.state != STATE_IDLE and rider.current_order is None:
                logger.warning("Rider %d had no active order; resetting to idle", rider.rider_id)
                rider.state = STATE_IDLE
            if rider.state == STATE_IDLE and rider.current_order is not None:
                rider.current_order = None
            rider.orders = [o for o in rider.orders if o.status != "completed"]
        if not isinstance(get_value("funds"), int):
            logger.warning("Fund balance corrupted; resetting to 0")
            from globalvar import set_value
            set_value("funds", 0)

    def cmd_start(self, args):
        """Create an order, recruit if needed, assign a rider and show the route.

        Args:
            args: Four coordinate tokens, or none to be prompted.
        """
        tokens = args
        if not tokens:
            tokens = self.inputs.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y: "
            ).split()
        rx, ry, cx, cy = self.inputs.parse_coordinates(tokens)
        order = self.orders.create_order((rx, ry), (cx, cy))
        new_rider = self.system.ensure_capacity()
        rider = self.orders.assign_order(order)
        if rider is None:
            print("No rider is available and funds are insufficient to recruit one. Order not assigned.")
            return

        route = PathPlanner.multi_stop_route(rider.position, [order.res_pos, order.cus_pos])
        distance = PathPlanner.route_length(route)
        eta = math.ceil(distance / rider.speed) if rider.speed > 0 else 0
        print(f"Order #{order.id} created at tick {order.created_tick}.")
        print(f"  Restaurant grid location: {order.res_pos}")
        print(f"  Customer grid location:   {order.cus_pos}")
        if new_rider is not None:
            print(f"  New rider recruited: Rider #{new_rider.rider_id} (cost {self.system.config('recruit_cost')})")
        else:
            print("  New rider recruited: no")
        print(f"  Assigned rider: #{rider.rider_id}  speed={rider.speed} units/tick  "
              f"state={rider.state}  active orders={len(rider.orders)}")
        print(f"  Route distance: {distance} units, estimated time: {eta} ticks")
        print(self.display.render_map(route))

    def cmd_status(self, args):
        """Print the system status snapshot."""
        print(self.display.render_status())

    def cmd_orders(self, args):
        """Print details of every order."""
        print(self.display.render_orders(self.orders.history()))

    def cmd_riders(self, args):
        """Print every rider's status-change log."""
        print(self.display.render_rider_logs())

    def cmd_tick(self, args):
        """Advance the simulation by one or more ticks and report events.

        Args:
            args: Optional number of ticks to advance.
        """
        count = self.inputs.parse_positive_int(args, 1, MAX_TICKS_PER_COMMAND)
        for _ in range(count):
            events = self.system.tick()
            for entry in events:
                print(self.display.format_event(entry))
        print(f"Advanced {count} tick(s). Current tick: {self.system.tick_count}. "
              f"Funds: {self.system.funds}")

    def cmd_map(self, args):
        """Print the ASCII map with current rider positions."""
        print(self.display.render_map())

    def cmd_save(self, args):
        """Save the current state to a JSON file.

        Args:
            args: Optional file path.
        """
        path = args[0] if args else DEFAULT_STATE_PATH
        if self.system.save_state(path):
            print(f"State saved to {path}.")
        else:
            print(f"Could not save state to {path}.")

    def cmd_history(self, args):
        """Print the command history."""
        for index, line in enumerate(self.inputs.history, start=1):
            print(f"  {index:>3}  {line}")

    def cmd_help(self, args):
        """Print the command help text."""
        print(self.display.help_text())

    def cmd_quit(self, args):
        """Stop the main loop."""
        self.system.stop()
        print("Goodbye.")


def main(argv=None):
    """Configure logging, create the application and run it.

    Args:
        argv: Optional list of command-line arguments; the first is the
            configuration file path.
    """
    logging.basicConfig(
        filename="dispatch.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = list(argv) if argv is not None else sys.argv[1:]
    config_path = args[0] if args else DEFAULT_CONFIG_PATH
    try:
        app = DispatchApp(config_path)
        app.run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")


if __name__ == "__main__":
    main()
