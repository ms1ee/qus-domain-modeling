"""Command-line entry point for the food delivery dispatch simulator."""

import logging
import math
import sys

from display import DisplayManager
from input_manager import InputManager, InputError
from order import OrderManager
from system import init_system

logger = logging.getLogger("dispatch")


class Application:
    """Main interactive loop."""

    def __init__(self, manager, out=None):
        self.manager = manager
        self.input = InputManager()
        self.display = DisplayManager()
        self.orders = OrderManager()
        self.out = out or sys.stdout

    def write(self, text=""):
        self.out.write(str(text) + "\n")

    def cmd_start(self, args):
        if args:
            coords = self.input.parse_coordinates(args)
        else:
            raw = input("Enter restaurant_x restaurant_y customer_x "
                        "customer_y: ")
            coords = self.input.parse_coordinates(raw)
        result = self.orders.create_order(*coords)
        order, rider = result["order"], result["rider"]
        length = self.display_route_info(order, rider, result)
        return length

    def display_route_info(self, order, rider, result):
        route = result["route"]
        from path_planner import PathPlanner
        length = PathPlanner.polyline_length(route)
        self.write("Order #%d created." % order.id)
        self.write("  Restaurant grid position: (%d, %d)" % order.res_pos)
        self.write("  Customer grid position:   (%d, %d)" % order.cus_pos)
        self.write("  New rider added: %s" % ("yes" if result["new_rider"]
                                              else "no"))
        self.write("  Assigned rider #%d at (%d, %d), speed %d units/tick"
                   % (rider.rider_id, rider.x, rider.y, rider.speed))
        self.write("  Route length: %d units, estimated time: %d ticks"
                   % (length, math.ceil(length / rider.speed)))
        self.write(self.display.render_map(self.manager.riders,
                                           self.manager.orders, route,
                                           highlight=rider.rider_id))
        return length

    def handle(self, line):
        """Process one command line; returns False when quitting."""
        cmd, args = self.input.parse_command(line)
        if cmd is None:
            return True
        try:
            if cmd == "start":
                self.cmd_start(args)
            elif cmd == "status":
                self.write(self.display.format_status(self.manager))
            elif cmd == "orders":
                self.write(self.display.format_orders(self.manager.orders))
            elif cmd == "riders":
                self.write(self.display.format_rider_logs(
                    self.manager.riders))
            elif cmd == "map":
                self.write(self.display.render_map(self.manager.riders,
                                                   self.manager.orders))
            elif cmd == "tick":
                n = self.input.parse_positive_int(args)
                self.manager.tick(n - 1)
                self.write("Advanced %d tick(s)." % n)
            elif cmd == "history":
                for i, h in enumerate(self.input.history, 1):
                    self.write("%3d  %s" % (i, h))
            elif cmd == "save":
                path = args[0] if args else "dispatch_state.json"
                self.manager.save_state(path)
                self.write("State saved to %s" % path)
            elif cmd == "help":
                self.write(self.display.format_help())
            elif cmd == "quit":
                self.manager.stop()
                self.write("Goodbye.")
                return False
            else:
                self.write("Unknown command '%s'. Type 'help'." % line.strip())
        except InputError as exc:
            self.write("Input error: %s" % exc)
        except (EOFError, KeyboardInterrupt):
            self.write("\nInput cancelled.")
        except Exception as exc:  # recovery from unexpected errors
            logger.exception("Unexpected error")
            self.write("Error: %s (system state recovered)" % exc)
            self.manager.check_consistency()
        return True

    def run(self):
        self.write("Food Delivery Dispatch Simulator - type 'help'.")
        while self.manager.running:
            try:
                line = input("[t=%d] > " % self.manager.time)
            except (EOFError, KeyboardInterrupt):
                self.write("")
                self.manager.stop()
                break
            if not self.handle(line):
                break
            self.manager.tick(1)
            issues = self.manager.check_consistency()
            for issue in issues:
                logger.warning("Consistency fix: %s", issue)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    level = logging.DEBUG if "--debug" in argv else logging.WARNING
    logging.basicConfig(level=level,
                        format="%(asctime)s %(name)s %(levelname)s "
                               "%(message)s")
    manager = init_system()
    Application(manager).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
