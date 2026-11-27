"""Command line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys

import config
import globalvar
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from path_planner import PathPlanner
from persistence import load_state, save_state
from system import init_system


class App:
    """Main application tying all managers together."""

    def __init__(self):
        globalvar._init()
        self.system = init_system()
        self.orders = OrderManager(self.system)
        self.display = DisplayManager()
        self.input = InputManager()

    # ---------------------------------------------------------------- commands
    def cmd_start(self, args):
        if not args:
            raw = input("Enter restaurant_x restaurant_y customer_x "
                        "customer_y (0-800): ")
            args = self.input.tokenize(raw)
        rx, ry, cx, cy = self.input.validate_coordinates(args)
        order = self.orders.create_order(rx, ry, cx, cy)
        rider, recruited = self.orders.dispatch(order)
        print("Order #%d created." % order.id)
        print("Restaurant: (%d,%d) -> grid %s centre %s"
              % (rx, ry, order.res_grid, order.res_pos))
        print("Customer:   (%d,%d) -> grid %s centre %s"
              % (cx, cy, order.cus_grid, order.cus_pos))
        print("New rider added: %s" % ("yes" if recruited else "no"))
        if rider is None:
            print("No rider available; order is pending (funds: %d)."
                  % self.system.funds)
            return
        route, dist, eta = self.orders.planned_route(rider, order)
        queued = len(rider.active_orders()) - 1
        print("Assigned to rider %d%s." % (
            rider.rider_id,
            "" if queued <= 0 else " (queued after %d order(s))" % queued))
        print(self.display.show_route(rider, order, route, dist, eta))

    def cmd_tick(self, args):
        n = 1
        if args:
            try:
                n = int(args[0])
            except ValueError:
                raise ValueError("tick expects an integer")
            if n < 1 or n > 100000:
                raise ValueError("tick count must be within 1-100000")
        # One tick is consumed by the main loop itself.
        for _ in range(n - 1):
            self.system.advance_tick()
        print("Advancing %d tick(s)." % n)

    def handle(self, cmd, args):
        """Dispatch a parsed command. Returns False if no tick should pass."""
        g = globalvar
        if cmd == "":
            return True
        if cmd == "start":
            self.cmd_start(args)
        elif cmd == "status":
            print(self.display.show_status(self.system.funds,
                                           self.system.tick,
                                           self.system.riders,
                                           self.orders.orders()))
        elif cmd == "orders":
            print(self.display.show_orders(self.orders.orders()))
        elif cmd == "riders":
            print(self.display.show_rider_logs(self.system.riders))
        elif cmd == "map":
            print(self.display.render_map(self.system.riders,
                                          self.orders.orders(),
                                          title="Map at tick %d"
                                          % self.system.tick))
        elif cmd == "tick":
            self.cmd_tick(args)
        elif cmd == "history":
            for i, h in enumerate(self.input.history, 1):
                print("%4d  %s" % (i, h))
            return False
        elif cmd == "save":
            print("State saved to %s" % save_state(args[0] if args else None))
            return False
        elif cmd == "load":
            print("State loaded from %s"
                  % load_state(args[0] if args else None))
            return False
        elif cmd == "help":
            print(self.input.help_text())
            return False
        elif cmd in ("quit", "exit"):
            g.set_value("running", False)
            return False
        elif cmd == "invalid_history":
            print("No such history entry.")
            return False
        else:
            print("Unknown command '%s'. Type 'help' for commands." % cmd)
            return False
        return True

    def run(self):
        """Main loop: each iteration represents one tick."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Funds: %d. Type 'help' for commands." % self.system.funds)
        while self.system.running:
            try:
                cmd, args = self.input.read_command(
                    "[t=%d] > " % self.system.tick)
            except (EOFError, KeyboardInterrupt):
                print()
                break
            try:
                advance = self.handle(cmd, args)
            except ValueError as exc:
                print("Input error: %s" % exc)
                continue
            except (OSError, KeyError) as exc:
                print("Error: %s" % exc)
                continue
            except Exception as exc:  # recovery mechanism
                logging.exception("Unexpected error")
                print("Unexpected error: %s. Recovering..." % exc)
                for fix in self.system.consistency_check():
                    print("  fixed: %s" % fix)
                continue
            if advance and self.system.running:
                self.system.advance_tick()
        print("Goodbye.")


def main(argv=None):
    """Program entry point."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch")
    parser.add_argument("--config", default=None, help="JSON config file")
    parser.add_argument("--debug", action="store_true", help="debug logs")
    ns = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if ns.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    config.load_config(ns.config)
    PathPlanner.SIZE = config.MAP_SIZE
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
