"""Command-line entry point for the Food Delivery Order Dispatch System."""

import logging
import sys

from config import CONFIG
from display import DisplayManager
from input_manager import HELP_TEXT, InputManager
from order import OrderManager
from path_planner import PathPlanner
from system import init_system

logger = logging.getLogger("dispatch")


def setup_logging(level=logging.WARNING):
    """Configure the dispatch logger for console output."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


class DispatchApp:
    """Interactive command loop tying all modules together.

    Each accepted command is one interaction step; simulated time advances
    through the ``tick`` command, one tick per unit.

    Attributes:
        system: SystemManager instance.
        orders: OrderManager instance.
        display: DisplayManager instance.
        inputs: InputManager instance.
    """

    def __init__(self, system):
        """Wire the application components together.

        Args:
            system: Initialised SystemManager.
        """
        self.system = system
        self.orders = OrderManager(system)
        self.display = DisplayManager(system)
        self.inputs = InputManager(CONFIG["history_size"])
        self.planner = PathPlanner()
        self._handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    def run(self):
        """Run the read-evaluate loop until the system stops."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = self.inputs.read_line()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line.strip():
                continue
            try:
                expanded = self.inputs.expand_history(line)
                command = self.inputs.parse(expanded)
                self.inputs.record(expanded)
            except ValueError as exc:
                print(f"Error: {exc}")
                continue
            try:
                self._handlers[command.name](command.arguments)
            except (EOFError, KeyboardInterrupt):
                print()
                break
            except Exception as exc:  # error recovery: keep the system running
                logger.exception("Command '%s' failed", command.name)
                print(f"Unexpected error: {exc}. System state preserved.")
        self.shutdown()

    def cmd_start(self, args):
        """Place a new order and assign it to the closest rider."""
        if args:
            rx, ry, cx, cy = args
        else:
            rx, ry, cx, cy = self.inputs.read_coordinates(self.inputs.read_line)

        order = self.orders.create_order((rx, ry), (cx, cy))
        created = self.system.check_recruitment()
        rider = self.orders.assign(order)

        print(f"Order #{order.id} created at tick {self.system.tick}")
        print(f"Restaurant: input ({rx},{ry}) -> grid centre {order.restaurant_center}")
        print(f"Customer:   input ({cx},{cy}) -> grid centre {order.customer_center}")
        if created:
            ids = ", ".join(f"#{rider_obj.rider_id}" for rider_obj in created)
            print(f"New rider added: {ids}")
        else:
            print("No new rider added.")
        if rider is None:
            print("No rider is available. The order is queued as 'unassigned' and "
                  "will be retried on each tick.")
            return
        print(f"Assigned to rider #{rider.rider_id}.")
        print(self.display.render_route(rider, order))

    def cmd_status(self, _args):
        """Show the system status snapshot."""
        print(self.display.render_status())

    def cmd_orders(self, _args):
        """Show all orders."""
        print(self.display.render_orders())

    def cmd_riders(self, _args):
        """Show the recorded status history for all riders."""
        print(self.display.render_rider_history())

    def cmd_map(self, _args):
        """Show the ASCII map with riders and active orders."""
        print(self.display.render_map())

    def cmd_tick(self, args):
        """Advance the simulation by the requested number of ticks."""
        steps = args[0] if args else 1
        for _ in range(steps):
            before = {order.id for order in self.orders.completed_orders()}
            self.orders.dispatch_pending()
            self.system.advance_tick()
            for order in self.orders.completed_orders():
                if order.id not in before:
                    print(f"  t={self.system.tick}: order #{order.id} delivered by rider "
                          f"#{order.rider_id} (time taken {order.time_taken} ticks)")
        print(f"Simulated {steps} tick(s). Current tick: {self.system.tick}")

    def cmd_history(self, _args):
        """Print the command history."""
        history = self.inputs.command_history
        if not history:
            print("History is empty.")
            return
        for index, entry in enumerate(history, start=1):
            print(f"  {index:>3}  {entry}")

    def cmd_help(self, _args):
        """Print the command help text."""
        print(HELP_TEXT)

    def cmd_quit(self, _args):
        """Stop the main loop."""
        self.system.is_running = False

    def shutdown(self):
        """Persist state if configured and print a farewell message."""
        if CONFIG["save_on_exit"]:
            try:
                self.system.save_state(CONFIG["save_file"])
                print(f"State saved to {CONFIG['save_file']}")
            except OSError as exc:
                print(f"Warning: could not save state: {exc}")
        print("Goodbye.")


def main():
    """Program entry point.

    Returns:
        Process exit code.
    """
    setup_logging()
    try:
        system = init_system()
    except Exception as exc:
        logger.exception("System initialisation failed")
        print(f"Fatal: could not initialise system: {exc}")
        return 1
    DispatchApp(system).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
