"""Command line entry point for the food delivery dispatch simulator."""

import logging
import math
import sys

import globalvar
from config import Configuration, save_state
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from system import init_system

try:  # command history / arrow keys where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

logging.basicConfig(level=logging.WARNING,
                    format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dispatch")


class DispatchApp:
    """Ties the managers together and runs the main loop."""

    def __init__(self, config_path="config.json"):
        self.config = Configuration(config_path)
        self.config.load()
        self.system = init_system(self.config.values)
        self.orders = OrderManager(self.system)
        self.display = DisplayManager()
        self.input = InputManager()

    def cmd_start(self, args):
        """Create and dispatch an order."""
        if not args:
            args = self.input.tokenize(
                input("Enter restaurant_x restaurant_y customer_x customer_y: "))
        coords = self.input.parse_coordinates(args)
        order = self.orders.create_order(coords[0:2], coords[2:4])
        rider, recruited = self.orders.dispatch(order)
        start = (rider.x, rider.y)
        path = rider.planner.plan_multi(start, rider.remaining_stops())
        ticks = math.ceil(path.length / rider.speed) if rider.speed else 0
        out = ["Order %d created." % order.id,
               "Restaurant grid: (%d, %d)   Customer grid: (%d, %d)" % (
                   order.res_x, order.res_y, order.cus_x, order.cus_y),
               "New rider added: %s" % (
                   "yes (rider %d, funds now %d)" % (recruited.rider_id,
                                                     self.system.funds)
                   if recruited else "no"),
               "Assigned rider: %d at (%d, %d), speed %d units/tick" % (
                   rider.rider_id, rider.x, rider.y, rider.speed),
               "Route: %s" % " -> ".join("(%d,%d)" % p for p in path.waypoints),
               "Route length: %d units, estimated time: %d ticks" % (
                   path.length, ticks),
               self.display.render_map([rider], [order], path.waypoints)]
        return "\n".join(out)

    def execute(self, name, args):
        """Execute a parsed command and return output text."""
        if name == "start":
            return self.cmd_start(args)
        if name == "status":
            return self.display.format_status(self.system)
        if name == "orders":
            return self.display.format_orders(self.orders.all_orders())
        if name == "riders":
            return self.display.format_rider_logs(self.system.riders)
        if name == "map":
            return self.display.render_map(self.system.riders,
                                           self.orders.all_orders())
        if name == "tick":
            n = int(args[0]) if args else 1
            if n < 0 or n > 100000:
                raise ValueError("tick count must be 0-100000")
            self.system.advance(n - 1 if n > 0 else 0)
            return "Advanced to tick %d." % (self.system.current_tick + 1)
        if name == "history":
            return "\n".join("%3d  %s" % (i + 1, c) for i, c in
                             enumerate(self.input.command_history)) or "(empty)"
        if name == "help":
            return self.input.help_text()
        if name == "quit":
            self.system.running = False
            return "Bye."
        return "Unknown command. Type 'help'."

    def save(self):
        """Persist system state to JSON."""
        data = self.system.snapshot()
        data["config"] = self.config.values
        save_state(self.config.values.get("state_file", "dispatch_state.json"), data)

    def run(self):
        """Main loop: each iteration is one tick."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.running:
            try:
                line = input("[t=%d] > " % self.system.current_tick)
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.running = False
                break
            name, args = self.input.parse(line)
            if name is None:
                if line.strip():
                    print("Unknown command. Type 'help'.")
                continue
            try:
                print(self.execute(name, args))
            except ValueError as exc:
                print("Error: %s" % exc)
            except Exception as exc:  # recover and continue
                logger.exception("Unexpected error")
                print("Unexpected error: %s (state recovered)" % exc)
                self.system.consistency_check()
            if self.system.running:
                self.system.advance(1)
        self.save()


def main(argv=None):
    """Program entry point."""
    argv = sys.argv[1:] if argv is None else argv
    app = DispatchApp(argv[0] if argv else "config.json")
    app.run()
    globalvar.set_value("running", False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
