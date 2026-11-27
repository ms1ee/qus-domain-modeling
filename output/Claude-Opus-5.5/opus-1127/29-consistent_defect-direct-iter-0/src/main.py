"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys

import globalvar
from config import DEFAULT_CONFIG_FILE, DEFAULT_SAVE_FILE, load_config
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from system import SystemManager

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

HELP = """Commands (shortcut in brackets):
  start [s]   rx ry cx cy   create an order (prompts if no coordinates)
  status [st]               system funds and rider states/orders
  orders [o]                details of all orders
  riders [r]                status-change log of all riders
  map [m]                   ASCII map of riders and active orders
  tick [t] [n]              advance simulation n ticks (default 1)
  run                       run until all orders are delivered
  save / load [file]        persist / restore state as JSON
  history                   show command history (!N or !! to repeat)
  help [h]                  this help
  quit / exit [q]           leave the program
Each command entered also advances the simulation by one tick."""


class Application:
    """Main loop tying together the managers."""

    def __init__(self, config=None, out=None):
        self.out = out or sys.stdout
        self.system = SystemManager(config)
        self.orders = OrderManager()
        self.inputs = InputManager()
        self.display = DisplayManager()

    def echo(self, text=""):
        print(text, file=self.out)

    def all_orders(self):
        return globalvar.get_value("orders") or []

    # -------------------------------------------------------------- commands
    def cmd_start(self, args):
        if not args:
            raw = input("Enter restaurant_x restaurant_y customer_x "
                        "customer_y: ")
            args = raw
        coords = self.inputs.validate_coordinates(args)
        order = self.orders.create_order(coords)
        new_riders = self.system.auto_recruit()
        rider = self.orders.assign(order)
        self.echo("Order %d created." % order.id)
        self.echo("  Restaurant grid cell: (%d, %d), center: (%d, %d)"
                  % (order.res_cell + order.res_pos))
        self.echo("  Customer   grid cell: (%d, %d), center: (%d, %d)"
                  % (order.cus_cell + order.cus_pos))
        if new_riders:
            self.echo("  New rider(s) added: %s (funds now %d)" % (
                ", ".join(str(r.rider_id) for r in new_riders),
                self.system.funds))
        else:
            self.echo("  No new rider added (funds %d)." % self.system.funds)
        if rider is None:
            self.echo("  No rider available; order is pending.")
            return
        self.echo("  Assigned to rider %d." % rider.rider_id)
        route = rider.remaining_route()
        if rider.current_order is None:
            from path_planner import PathPlanner
            stops = []
            for o in rider.active_orders():
                stops.extend([o.res_pos, o.cus_pos])
            route = PathPlanner.route(rider.position, stops)
        self.echo(self.display.render_route(
            rider, route, self.system.riders, self.all_orders()))

    def cmd_tick(self, n):
        for _ in range(n):
            self.step()
        self.echo("Advanced %d tick(s). Time is now %d."
                  % (n, self.system.time))

    def cmd_run(self):
        limit = 100000
        count = 0
        while not self.system.all_delivered() and count < limit:
            self.step()
            count += 1
        self.echo("Ran %d tick(s). Time is now %d." % (count,
                                                      self.system.time))

    def step(self):
        """One simulation tick, assigning leftover pending orders."""
        if self.orders.pending_orders():
            self.system.auto_recruit()
            self.orders.assign_pending()
        self.system.tick()

    def handle(self, line):
        """Process one command line. Returns False to quit."""
        cmd, args = self.inputs.parse_command(line)
        if cmd is None:
            return True
        if cmd == "quit":
            self.system.stop()
            return False
        try:
            if cmd == "start":
                self.cmd_start(args)
            elif cmd == "status":
                self.echo(self.display.render_status(
                    self.system.funds, self.system.riders, self.system.time))
            elif cmd == "orders":
                self.echo(self.display.render_orders(self.all_orders()))
            elif cmd == "riders":
                self.echo(self.display.render_rider_logs(self.system.riders))
            elif cmd == "map":
                self.echo(self.display.render_map(
                    self.system.riders, self.all_orders()))
            elif cmd == "tick":
                self.cmd_tick(self.inputs.parse_positive_int(args))
                return True
            elif cmd == "run":
                self.cmd_run()
                return True
            elif cmd == "save":
                path = self.system.save(args[0] if args
                                        else DEFAULT_SAVE_FILE)
                self.echo("State saved to %s." % path)
            elif cmd == "load":
                path = self.system.load(args[0] if args
                                        else DEFAULT_SAVE_FILE)
                self.echo("State loaded from %s." % path)
            elif cmd == "history":
                for i, h in enumerate(self.inputs.history, 1):
                    self.echo("%4d  %s" % (i, h))
            elif cmd == "help":
                self.echo(HELP)
            else:
                self.echo("Unknown command '%s'. Type 'help'." % args[0])
                return True
        except ValueError as exc:
            self.echo("Input error: %s" % exc)
            return True
        except (OSError, KeyError) as exc:
            self.echo("Error: %s" % exc)
            return True
        except Exception as exc:  # graceful recovery
            logging.exception("Unexpected error")
            self.echo("Unexpected error: %s (state recovered)" % exc)
            for msg in self.system.check_consistency():
                self.echo("  fixed: %s" % msg)
            return True
        self.step()
        return True

    def run(self):
        """Main interactive loop: each iteration is one tick."""
        self.echo("Food Delivery Dispatch Simulator. Type 'help'.")
        while self.system.running:
            try:
                line = input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self.echo()
                break
            if not self.handle(line):
                break
        self.echo("Goodbye.")


def main(argv=None):
    """Program entry point."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch "
                                                 "simulator")
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE)
    parser.add_argument("--debug", action="store_true")
    ns = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if ns.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    Application(load_config(ns.config)).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
