"""Command-line entry point for the Food Delivery Order Dispatch simulator.

Run with::

    python src/main.py [--config config.json] [--debug]

The main loop reads commands; every simulated tick moves all riders and
dispatches any pending orders.
"""

import argparse
import logging
import math
import sys

from display import DisplayManager
from input_manager import HELP_TEXT, InputManager
from order import OrderManager
from order_model import STATUS_COMPLETED
from path_planner import PathPlanner
from system import DEFAULT_STATE_FILE, init_system, load_config, save_state

logger = logging.getLogger("dispatch")

MAX_TICKS_PER_ORDER = 1000


class DispatchApp:
    """Interactive application wiring all managers together.

    Attributes:
        system (SystemManager): funds, riders and clock.
        orders (OrderManager): order creation and assignment.
        planner (PathPlanner): route computation for display.
        display (DisplayManager): text rendering.
        inputs (InputManager): command parsing and history.
        config (dict): effective configuration parameters.
    """

    def __init__(self, config_path=None, input_func=input, output=print):
        """Create the application.

        Args:
            config_path (str | None): optional JSON configuration file.
            input_func (callable): function used to read input.
            output (callable): function used to print output.
        """
        self.system = init_system()
        self.config = load_config(config_path)
        self.system.funds = self.config["initial_funds"]
        self.system.recruit_cost = self.config["recruit_cost"]
        self.system.recruit_threshold = self.config["recruit_threshold"]
        self.orders = OrderManager()
        self.planner = PathPlanner()
        self.display = DisplayManager()
        self.inputs = InputManager(input_func)
        self._out = output
        self._handlers = {
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

    def out(self, text=""):
        """Print a line of output."""
        self._out(text)

    def run(self):
        """Run the main command loop until quit, EOF or interrupt."""
        self.out("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.running:
            try:
                line = self.inputs.read_command()
            except (EOFError, KeyboardInterrupt):
                self.out()
                break
            except ValueError as exc:
                self.out(f"Error: {exc}")
                continue
            command, args = self.inputs.parse(line)
            if command is None:
                continue
            self.execute(command, args)
        self.out("Goodbye.")

    def execute(self, command, args):
        """Run one command, converting failures into friendly messages.

        Args:
            command (str): canonical command name.
            args (list[str]): command arguments.
        """
        handler = self._handlers.get(command)
        if handler is None:
            self.out(f"Unknown command '{command}'. Type 'help' for the list of commands.")
            return
        try:
            handler(args)
        except ValueError as exc:
            self.out(f"Error: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Command '%s' failed", command)
            self.out(f"Unexpected error while running '{command}': {exc}. State preserved.")

    def _advance(self):
        """Advance the simulation one tick and dispatch pending orders."""
        self.system.tick()
        self._dispatch_pending()

    def _dispatch_pending(self):
        """Recruit riders as required and assign every pending order.

        Returns:
            list[Rider]: riders recruited during this dispatch.
        """
        new_riders = []
        while True:
            pending = self.orders.pending_orders()
            if not pending:
                break
            rider = self.system.recruit_if_needed(len(pending))
            if rider is None:
                break
            new_riders.append(rider)
        for order in self.orders.pending_orders():
            self.orders.assign(order)
        return new_riders

    def _find_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for rider in self.system.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def cmd_start(self, args):
        """Place an order and run the simulation until it is delivered.

        Args:
            args (list[str]): ``rx ry cx cy`` coordinates.
        """
        rx, ry, cx, cy = self.inputs.parse_coordinates(args)
        order = self.orders.create_order((rx, ry), (cx, cy))
        new_riders = self._dispatch_pending()

        self.out(f"Order #{order.id} created at tick {order.start_time}.")
        self.out(
            f"  Restaurant: input ({rx}, {ry}) -> grid cell "
            f"({rx // 100}, {ry // 100}), centre {order.res_pos}"
        )
        self.out(
            f"  Customer:   input ({cx}, {cy}) -> grid cell "
            f"({cx // 100}, {cy // 100}), centre {order.cus_pos}"
        )
        if new_riders:
            ids = ", ".join(f"#{r.rider_id}" for r in new_riders)
            self.out(f"  New rider added: {ids} (funds now {self.system.funds})")
        else:
            self.out("  New rider added: no")

        if order.status == "pending":
            self.out("  No rider available (insufficient funds); order is queued.")
            return

        rider = self._find_rider(order.rider_id)
        leg1 = self.planner.plan(rider.position(), order.res_pos, rider.speed)
        leg2 = self.planner.plan(order.res_pos, order.cus_pos, rider.speed)
        route_points = [(p.x, p.y) for p in leg1.points] + [
            (p.x, p.y) for p in leg2.points[1:]
        ]
        estimated = leg1.estimated_ticks + leg2.estimated_ticks
        self.out(
            f"  Assigned to Rider #{rider.rider_id} at ({rider.x}, {rider.y}); "
            f"speed {rider.speed} units/tick"
        )
        self.out(
            f"  Route: {' -> '.join(f'({x},{y})' for x, y in route_points)}"
        )
        self.out(
            f"  Estimated time: {estimated} ticks "
            f"(distance {leg1.total_distance + leg2.total_distance:.0f} units; "
            "excludes any queued orders)"
        )
        self.out(self.display.render_map(self.system.riders, self.orders.orders, route_points))

        ticks = 0
        while not order.is_completed() and ticks < MAX_TICKS_PER_ORDER:
            self._advance()
            ticks += 1
        if order.status == STATUS_COMPLETED:
            self.out(
                f"Order #{order.id} delivered at tick {order.completion_time} "
                f"(time taken {order.time_taken} ticks, distance {order.distance:.1f})."
            )
        else:
            self.out(f"Order #{order.id} not delivered within {MAX_TICKS_PER_ORDER} ticks.")

    def cmd_status(self, args):
        """Show funds, riders, positions, states and order lists."""
        self.out(self.display.render_status(self.system))
        issues = self.system.check_consistency()
        if issues:
            self.out("Consistency warnings: " + "; ".join(issues))

    def cmd_orders(self, args):
        """Show details of all orders."""
        self.out(self.display.render_orders(self.orders.orders))

    def cmd_riders(self, args):
        """Show every recorded rider status change."""
        self.out(self.display.render_rider_history(self.system.riders))

    def cmd_map(self, args):
        """Show the ASCII map with riders and active orders."""
        self.out(self.display.render_map(self.system.riders, self.orders.orders))

    def cmd_tick(self, args):
        """Advance the simulation by one or more ticks.

        Args:
            args (list[str]): optional tick count.
        """
        count = self.inputs.parse_count(args)
        for _ in range(count):
            self._advance()
        self.out(
            f"Advanced {count} tick(s). Simulated time: {self.system.simulated_time}. "
            f"Funds: {self.system.funds}. Riders: {len(self.system.riders)}."
        )

    def cmd_save(self, args):
        """Save the state to a JSON file.

        Args:
            args (list[str]): optional file path.
        """
        path = args[0] if args else DEFAULT_STATE_FILE
        try:
            save_state(path, self.system, self.orders)
        except OSError as exc:
            raise ValueError(f"could not write '{path}': {exc}") from None
        self.out(f"State saved to {path}.")

    def cmd_help(self, args):
        """Show the command list."""
        self.out(HELP_TEXT)

    def cmd_quit(self, args):
        """Stop the main loop."""
        self.system.running = False


def main(argv=None):
    """Parse arguments, configure logging and run the application.

    Args:
        argv (list[str] | None): command-line arguments.

    Returns:
        int: process exit status.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None, help="path to a JSON configuration file")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = DispatchApp(config_path=args.config)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
