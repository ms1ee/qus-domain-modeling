"""Command-line entry point for the food delivery dispatch simulator.

Run with:  python src/main.py [--config dispatch_config.json] [--debug]
"""

import argparse
import logging
import os
import sys

from display_manager import DisplayManager
from input_manager import InputManager
from order_model import ACTIVE_ORDER_STATUSES
from path_planner import PathPlanner
from system import SystemManager

logger = logging.getLogger("dispatch")

DEFAULT_CONFIG = "dispatch_config.json"
MAX_RUN_TICKS = 10000
MAX_TICK_STEP = 10000

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy]  (s)   Place an order: restaurant then customer coordinates (0-1000)
  status               (st)  System funds, riders and their state
  orders               (o)   All orders with time, distance and rider
  riders               (r)   Full status-change history of every rider
  map                  (m)   ASCII map with riders and active orders
  tick [n]             (t)   Advance the simulation by n ticks (default 1)
  run                        Advance until all active orders are finished
  save [path]                Save the configuration/state as JSON
  help                 (h)   Show this help
  quit / exit          (q)   Save (if configured) and exit
Notes: rider speed is 20 units/tick; one tick = one time unit.
Up/Down arrows recall command history when readline is available.
"""


class DispatchApp:
    """Interactive application wiring the managers together."""

    def __init__(self, config_path=DEFAULT_CONFIG):
        """Create the application and optionally load a saved configuration.

        Args:
            config_path: JSON file path, or None/empty to disable persistence.
        """
        self.config_path = config_path or None
        self.system = SystemManager()
        self.display = DisplayManager()
        self.inputs = InputManager()
        self.handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "run": self.cmd_run,
            "save": self.cmd_save,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }
        if self.config_path and os.path.exists(self.config_path):
            try:
                self.system.load_config(self.config_path)
                self.display.show_message(f"Loaded configuration from {self.config_path}.")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                logger.warning("Could not load configuration: %s", exc)
                self.display.show_error(
                    f"Could not load {self.config_path}: {exc}. Starting fresh."
                )
                self.system = SystemManager()

    def run(self):
        """Run the main command loop until quit or end of input."""
        self.display.show_message("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.is_running():
            try:
                line = self.inputs.read_line("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.stop()
                break
            if not line:
                continue
            try:
                name, args = self.inputs.parse_command(line)
                self.handlers[name](args)
            except ValueError as exc:
                self.display.show_error(str(exc))
            except Exception as exc:  # recovery: keep the simulation alive
                logger.exception("Unexpected error while handling '%s'", line)
                self.display.show_error(f"Unexpected error: {exc}. State preserved.")
                self._recover()
        self.shutdown()

    def _recover(self):
        """Run a consistency check after an unexpected failure and report it."""
        issues = self.system.check_consistency()
        for issue in issues:
            logger.warning("Consistency issue: %s", issue)

    def shutdown(self):
        """Save the configuration when persistence is enabled and say goodbye."""
        if self.config_path:
            try:
                self.system.save_config(self.config_path)
                self.display.show_message(f"State saved to {self.config_path}.")
            except OSError as exc:
                self.display.show_error(f"Could not save configuration: {exc}")
        self.display.show_message("Goodbye.")

    # ----- command handlers --------------------------------------------------
    def cmd_start(self, args):
        """Place an order and show the assigned rider's route."""
        if args:
            coords = self.inputs.parse_coordinates(args)
        else:
            coords = self.inputs.prompt_coordinates(
                "Enter restaurant_x restaurant_y customer_x customer_y (blank to cancel): "
            )
            if coords is None:
                self.display.show_message("Order cancelled.")
                return
        restaurant = (coords[0], coords[1])
        customer = (coords[2], coords[3])
        order, rider, new_rider = self.system.submit_order(restaurant, customer)

        self.display.show_message(f"Order #{order.id} created at tick {order.created_tick}.")
        self.display.show_message(
            f"Restaurant input {restaurant} -> grid {order.res_pos}; "
            f"Customer input {customer} -> grid {order.cus_pos}"
        )
        if new_rider:
            self.display.show_message(
                f"New rider added: Rider #{rider.rider_id if rider else '?'} "
                f"(cost {self.system_recruit_cost()}, funds now {self.system.funds})."
            )
        else:
            self.display.show_message("New rider added: No")

        if rider is None:
            self.display.show_message(
                f"Order #{order.id} is pending: no rider available "
                f"(funds {self.system.funds}, need >= 300 to recruit)."
            )
            return

        route = PathPlanner.build_route(
            (rider.x, rider.y), [order.res_pos, order.cus_pos]
        )
        ticks = PathPlanner.estimate_ticks(route, rider.speed)
        self.display.show_message(
            f"Order #{order.id} assigned to Rider #{rider.rider_id}."
        )
        self.display.show_route(rider, order, route, ticks)

    def system_recruit_cost(self):
        """Return the configured recruitment cost."""
        from system import PARAMS
        return PARAMS["recruit_cost"]

    def cmd_status(self, args):
        """Show the system snapshot."""
        self.display.show_status(
            self.system.funds,
            self.system.riders,
            self.system.pending_order_count(),
            self.system.check_consistency(),
        )

    def cmd_orders(self, args):
        """Show the order table."""
        self.display.show_orders(self.system.order_manager.all_orders())

    def cmd_riders(self, args):
        """Show each rider's recorded event history."""
        self.display.show_rider_history(self.system.riders)

    def cmd_map(self, args):
        """Show the ASCII map with riders and active orders."""
        active = [o for o in self.system.order_manager.all_orders()
                  if o.status in ACTIVE_ORDER_STATUSES or o.status == "pending"]
        self.display.show_map(self.system.riders, active)

    def cmd_tick(self, args):
        """Advance the simulation by one or more ticks."""
        steps = 1
        if args:
            steps = self.inputs.parse_integer(args[0], "tick count")
            if not 1 <= steps <= MAX_TICK_STEP:
                raise ValueError(f"tick count must be between 1 and {MAX_TICK_STEP}.")
        completed = 0
        for _ in range(steps):
            completed += self.system.tick()
        self.display.show_message(
            f"Advanced {steps} tick(s). Now at tick {self.system.current_tick()}. "
            f"Orders completed: {completed}. Active orders: "
            f"{sum(1 for o in self.system.order_manager.all_orders() if o.status in ACTIVE_ORDER_STATUSES)}."
        )

    def cmd_run(self, args):
        """Advance the simulation until no active orders remain."""
        steps = 0
        completed = 0
        while self.system.has_active_orders() and steps < MAX_RUN_TICKS:
            completed += self.system.tick()
            steps += 1
        if self.system.has_active_orders():
            self.display.show_error(f"Stopped after {MAX_RUN_TICKS} ticks; orders still active.")
        self.display.show_message(
            f"Run finished after {steps} tick(s). Orders completed: {completed}. "
            f"Current tick: {self.system.current_tick()}."
        )

    def cmd_save(self, args):
        """Save the configuration to a file."""
        path = args[0] if args else self.config_path
        if not path:
            raise ValueError("No file path given and no default configuration file set.")
        try:
            self.system.save_config(path)
        except OSError as exc:
            raise ValueError(f"Could not save to {path}: {exc}") from exc
        self.display.show_message(f"State saved to {path}.")

    def cmd_help(self, args):
        """Print the command reference."""
        print(HELP_TEXT)

    def cmd_quit(self, args):
        """Stop the main loop; state is saved on shutdown."""
        self.system.stop()


def main(argv=None):
    """Parse command-line arguments and run the simulator.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 on normal exit).
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help="JSON configuration/state file ('' disables persistence)")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = DispatchApp(args.config)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
