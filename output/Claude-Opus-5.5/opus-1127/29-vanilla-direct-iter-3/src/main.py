"""Command-line entry point for the food delivery dispatch simulator.

Each iteration of the main loop represents one simulated tick.
"""

import logging
import math
import os
import sys

import globalvar as gv
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from system import SystemManager, init_system, load_config

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
DEFAULT_STATE = "dispatch_state.json"

HELP = """Commands (shortcut):
  start (s) [rx ry cx cy]  create an order (coords 0-800)
  status (st)              system funds and rider states
  orders (o)               all order details
  riders (r)               rider status-change log
  map (m)                  show ASCII map
  tick (t) [n]             advance n ticks
  run (ru)                 run until all orders delivered
  save [file] / load [file]  persist state as JSON
  history (hi)             command history
  help (h)                 this help
  quit/exit (q)            exit"""


class App:
    """Glue between the managers and the command line."""

    def __init__(self):
        gv._init()
        init_system(load_config(CONFIG_PATH))
        self.system = SystemManager()
        self.orders = OrderManager(self.system)
        self.display = DisplayManager()
        self.input = InputManager()

    def cmd_start(self, args):
        if not args.strip():
            args = input("Enter [restaurant_x, restaurant_y, customer_x, "
                         "customer_y]: ")
        raw = self.input.parse_order_input(args)
        order, new_rider, rider = self.orders.dispatch(raw)
        print("Order %d created." % order.id)
        print("  Restaurant grid position: (%d, %d)" % order.res_pos)
        print("  Customer grid position:   (%d, %d)" % order.cus_pos)
        if new_rider is not None:
            print("  New rider added: yes (rider %d, funds now %d)" % (
                new_rider.rider_id, self.system.funds))
        else:
            print("  New rider added: no")
        if rider is None:
            print("  No rider available; order is waiting for assignment.")
            return
        route = rider.remaining_route()
        from path_planner import PathPlanner
        length = PathPlanner.path_length(route)
        print("  Assigned to rider %d at (%d, %d), speed %d units/tick" % (
            rider.rider_id, rider.x, rider.y, rider.speed))
        print("  Route length %d units, estimated time %d ticks" % (
            length, math.ceil(length / float(rider.speed or 1))))
        print(self.display.render_map(self.system.riders,
                                      gv.get_value("orders") or [], route))

    def cmd_tick(self, args):
        n = self.input.parse_positive_int(args, 1)
        for _ in range(n):
            self.system.tick(self.orders)
        print("Advanced %d tick(s). Time is now %d." % (n, self.system.time))

    def cmd_run(self, _args):
        steps = 0
        while not self.system.all_idle() and steps < 100000:
            self.system.tick(self.orders)
            steps += 1
        print("Ran %d tick(s). Time is now %d." % (steps, self.system.time))
        if not self.system.all_idle():
            print("Some orders could not be completed (no riders available).")

    def handle(self, cmd, args):
        """Dispatch a parsed command."""
        if cmd == "start":
            self.cmd_start(args)
        elif cmd == "status":
            print(self.display.format_status(self.system.riders))
        elif cmd == "orders":
            print(self.display.format_orders(gv.get_value("orders") or []))
        elif cmd == "riders":
            print(self.display.format_rider_logs(self.system.riders))
        elif cmd == "map":
            print(self.display.render_map(self.system.riders,
                                          gv.get_value("orders") or []))
        elif cmd == "tick":
            self.cmd_tick(args)
        elif cmd == "run":
            self.cmd_run(args)
        elif cmd == "save":
            path = args.strip() or DEFAULT_STATE
            self.system.save_state(path)
            print("State saved to %s" % path)
        elif cmd == "load":
            path = args.strip() or DEFAULT_STATE
            self.system.load_state(path)
            print("State loaded from %s" % path)
        elif cmd == "history":
            for i, h in enumerate(self.input.history, 1):
                print("%4d  %s" % (i, h))
        elif cmd == "help":
            print(HELP)
        elif cmd == "quit":
            gv.set_value("running", False)
            print("Goodbye.")
        elif cmd and cmd.startswith("unknown:"):
            print("Unknown command '%s'. Type 'help'." % cmd[8:])

    def run(self):
        """Main loop: one iteration == one tick."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while gv.get_value("running"):
            try:
                line = input("dispatch[t=%d]> " % self.system.time)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
                continue
            cmd, args = self.input.parse_command(line)
            try:
                self.handle(cmd, args)
            except ValueError as exc:
                print("Input error: %s" % exc)
            except (OSError, KeyError) as exc:
                print("Error: %s" % exc)
            except Exception as exc:  # recover from unexpected failures
                logging.getLogger("dispatch").exception("Unexpected error")
                print("Unexpected error: %s (state recovered)" % exc)
                self.system.consistency_check()
            if gv.get_value("running"):
                self.system.tick(self.orders)


def main():
    """Program entry point."""
    level = logging.DEBUG if "--debug" in sys.argv else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
    App().run()


if __name__ == "__main__":
    main()
