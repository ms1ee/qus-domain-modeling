"""Command-line entry point for the Food Delivery Order Dispatch simulator.

Run from the project root with:  python src/main.py [config.json]
"""

import logging
import sys

from display import DisplayManager
from input_manager import InputError, InputManager
from order import OrderManager
from path_planner import PathPlanner
from system import init_system, save_state

LOGGER = logging.getLogger("dispatch.main")

MAX_RUN_TICKS = 10000

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order (restaurant then customer, 0-1000)  [s]
  status               Show funds, riders and their orders               [st]
  orders               Show all order details                            [o]
  riders               Show every rider status change log                [r]
  map                  Show the ASCII map with riders and orders         [m]
  tick [n]             Advance simulated time by n ticks (default 1)     [t]
  run                  Advance time until all orders are delivered       [u]
  save [path]          Save state to a JSON file
  history              Show command history                              [hist]
  !! / !n              Repeat the last / n-th command
  help                 Show this help                                    [h]
  quit | exit          Leave the program                                 [q/e]"""


class DispatchApp:
    """Wires together the managers and runs the interactive loop."""

    def __init__(self, config_path=None):
        """Initialise all subsystems.

        Args:
            config_path: Optional JSON configuration file.
        """
        self.system = init_system(config_path)
        self.orders = OrderManager(self.system)
        self.display = DisplayManager(self.system)
        self.inputs = InputManager()
        self.planner = PathPlanner()
        self.handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "run": self.cmd_run,
            "save": self.cmd_save,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    def run(self):
        """Run the interactive main loop until the system stops."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands.")
        while self.system.running:
            try:
                line = self.inputs.read_line("dispatch> ")
            except KeyboardInterrupt:
                print()
                break
            try:
                name, args = self.inputs.parse_command(line)
            except InputError as exc:
                print(f"Input error: {exc}")
                continue
            if not name:
                continue
            handler = self.handlers.get(name)
            if handler is None:
                print(f"Unknown command '{name}'. Type 'help' for commands.")
                continue
            try:
                handler(args)
            except InputError as exc:
                print(f"Input error: {exc}")
            except Exception:  # keep the simulator alive on unexpected errors
                LOGGER.exception("Unexpected error while running '%s'", name)
                print("An unexpected error occurred; checking system state.")
                for issue in self.system.check_consistency():
                    print(f"Warning: {issue}")
        print("Goodbye.")

    def advance(self, steps):
        """Advance the simulation and report newly delivered orders."""
        for _ in range(steps):
            delivered_before = {o.id for o in self.orders.completed_orders()}
            tick = self.system.tick()
            self.orders.assign_pending()
            for order in self.orders.completed_orders():
                if order.id not in delivered_before:
                    print(f"[t={tick}] Order #{order.id} delivered by rider "
                          f"#{order.rider_id} (took {order.time_taken} ticks)")
        for issue in self.system.check_consistency():
            print(f"Warning: {issue}")

    def _active_orders(self):
        """Return orders that are not yet completed."""
        return [o for o in self.orders.orders if o.status != "completed"]

    def cmd_start(self, args):
        """Place a new order and show the assigned rider's route."""
        if not args:
            args = self.inputs.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y: ").split()
        rx, ry, cx, cy = self.inputs.parse_coordinates(args)
        order, rider, added = self.orders.submit_order((rx, ry), (cx, cy))
        print(f"Restaurant grid point: ({order.restaurant_x}, {order.restaurant_y})")
        print(f"Customer grid point: ({order.customer_x}, {order.customer_y})")
        if added:
            print(f"New rider added: yes (rider #{self.system.riders[-1].rider_id}, "
                  f"funds now {self.system.funds})")
        else:
            print("New rider added: no")
        if rider is None:
            print(f"No rider available (funds {self.system.funds}); "
                  f"order #{order.id} is pending.")
            return
        print(f"Order #{order.id} assigned to rider #{rider.rider_id}.")
        legs = [(order.restaurant_x, order.restaurant_y),
                (order.customer_x, order.customer_y)]
        route = self.planner.plan_multi_stop((rider.x, rider.y), legs)
        total = self.planner.route_length(route)
        ticks = self.planner.estimate_ticks(total, rider.speed)
        print(f"Route distance: {total} units | Speed: {rider.speed} units/tick | "
              f"Estimated time: {ticks} ticks (excludes queued orders)")
        print(self.display.map_text(orders=[order], route=route))

    def cmd_status(self, args):
        """Print the system status snapshot."""
        print(self.display.status_report())

    def cmd_orders(self, args):
        """Print the table of all orders."""
        print(self.display.orders_report(self.orders.orders))

    def cmd_riders(self, args):
        """Print the rider status change history."""
        print(self.display.riders_report())

    def cmd_map(self, args):
        """Print the ASCII map with riders and active orders."""
        print(self.display.map_text(orders=self._active_orders()))

    def cmd_tick(self, args):
        """Advance the simulation by one or more ticks."""
        steps = 1
        if args:
            try:
                steps = int(args[0])
            except ValueError:
                raise InputError("Tick count must be an integer.")
        if not 1 <= steps <= MAX_RUN_TICKS:
            raise InputError(f"Tick count must be between 1 and {MAX_RUN_TICKS}.")
        self.advance(steps)

    def cmd_run(self, args):
        """Advance until every order is delivered (bounded by MAX_RUN_TICKS)."""
        if not self._active_orders():
            print("No active orders to run.")
            return
        steps = 0
        while self._active_orders() and steps < MAX_RUN_TICKS:
            self.advance(1)
            steps += 1
        if self._active_orders():
            print(f"Stopped after {steps} ticks; some orders are still pending "
                  f"(funds {self.system.funds}).")
        else:
            print(f"All orders delivered after {steps} ticks.")

    def cmd_save(self, args):
        """Save the state to a JSON file."""
        path = args[0] if args else "dispatch_state.json"
        try:
            save_state(path, self.system, self.orders.orders)
        except OSError as exc:
            print(f"Could not save state: {exc}")
            return
        print(f"State saved to {path}.")

    def cmd_history(self, args):
        """Print the numbered command history."""
        history = self.inputs.history()
        if not history:
            print("No command history.")
            return
        for index, entry in enumerate(history, start=1):
            print(f"{index:>4}  {entry}")

    def cmd_help(self, args):
        """Print the command help text."""
        print(HELP_TEXT)

    def cmd_quit(self, args):
        """Stop the main loop."""
        self.system.shutdown()


def main(argv=None):
    """Program entry point.

    Args:
        argv: Optional argument list; the first item may be a config path.

    Returns:
        Process exit code.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config_path = args[0] if args else "config.json"
    app = DispatchApp(config_path)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
