"""Command-line entry point of the food delivery dispatch simulator."""

import argparse
import logging
import sys

import globalvar
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from path_planner import PathPlanner
from system import SystemManager, load_config

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

HELP = """Commands:
  start (s)     input an order: rx ry cx cy (0-800)
  status (st)   system snapshot
  orders (o)    all orders
  riders (r)    rider status change log
  map (m)       ASCII map
  tick (t) [n]  advance simulation n ticks
  run           run until all orders are delivered
  save/load [f] persist state to JSON
  history       command history
  quit/exit (q) exit"""


class App:
    """Main application tying together all managers."""

    def __init__(self, funds=1000):
        self.system = SystemManager(funds)
        self.orders = OrderManager()
        self.inputs = InputManager()
        self.display = DisplayManager()

    def out(self, text):
        print(text)

    def cmd_start(self, args):
        text = " ".join(args) if args else input("Enter rx ry cx cy: ")
        coords = self.inputs.parse_coordinates(text)
        order = self.orders.create_order(coords)
        new = self.system.auto_recruit()
        results = self.orders.dispatch_pending()
        self.out("Order %d: restaurant %s -> customer %s" % (order.id, order.res_pos, order.cus_pos))
        self.out("New rider added: %s" % (", ".join(str(r.rider_id) for r in new) if new else "no"))
        for o, rider, path in results:
            if o is order:
                self.out("Assigned to rider %s (speed %d, distance %d, est. time %d ticks)" % (
                    rider.rider_id, rider.speed, o.distance, o.estimated_time))
                self.out(self.display.render_map([rider], [o], path))
                break
        else:
            self.out("Order is pending: no rider available.")

    def cmd_tick(self, args):
        n = int(args[0]) if args else 1
        for _ in range(max(0, n)):
            self.system.tick(self.orders)
        self.out("Time is now %d" % self.system.time)

    def cmd_run(self, args):
        limit = 10000
        while limit and any(o.status != "completed" for o in self.orders.all_orders()):
            self.system.tick(self.orders)
            limit -= 1
        self.out("All deliverable orders done at time %d" % self.system.time)

    def handle(self, line):
        cmd, args = self.inputs.parse_command(line)
        if cmd is None:
            return
        try:
            if cmd == "start":
                self.cmd_start(args)
            elif cmd == "status":
                self.out(self.display.status(self.system.funds, self.system.riders, self.system.time))
            elif cmd == "orders":
                self.out(self.display.orders_table(self.orders.all_orders()))
            elif cmd == "riders":
                self.out(self.display.rider_logs(self.system.riders))
            elif cmd == "map":
                self.out(self.display.render_map(self.system.riders, self.orders.all_orders()))
            elif cmd == "tick":
                self.cmd_tick(args)
                return
            elif cmd == "run":
                self.cmd_run(args)
                return
            elif cmd == "save":
                self.out("Saved to %s" % self.system.save(*args[:1]))
            elif cmd == "load":
                self.out("Loaded %s" % self.system.load(*args[:1]))
            elif cmd == "history":
                self.out("\n".join("%d %s" % (i + 1, h) for i, h in enumerate(self.inputs.history)))
            elif cmd == "help":
                self.out(HELP)
            elif cmd == "quit":
                self.system.stop()
                return
            else:
                self.out("Unknown command '%s'. Type 'help'." % cmd)
                return
        except ValueError as exc:
            self.out("Error: %s" % exc)
            return
        except Exception as exc:  # recovery
            logging.exception("Unexpected error")
            self.out("Unexpected error: %s (state recovered)" % exc)
            self.system.check_consistency()
            return
        # each processed command iteration represents one tick
        self.system.tick(self.orders)

    def loop(self):
        self.out("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while globalvar.get_value("running", True):
            try:
                line = input("> ")
            except (EOFError, KeyboardInterrupt):
                break
            self.handle(line)
        self.out("Bye.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="JSON config file with system parameters")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)
    funds = 1000
    if args.config:
        try:
            funds = int(load_config(args.config).get("funds", 1000))
        except (OSError, ValueError) as exc:
            print("Could not load config: %s" % exc)
    App(funds).loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
