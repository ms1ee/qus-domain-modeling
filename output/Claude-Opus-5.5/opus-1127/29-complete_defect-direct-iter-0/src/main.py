"""Command-line entry point for the food delivery dispatch simulator."""

import logging
import math
import sys

from display import DisplayManager
from input_manager import COMMANDS, InputManager
from path_planner import PathPlanner
from system import SystemManager

HELP = """Commands:
  start [rx ry cx cy]  (s)   place an order
  status               (st)  system snapshot
  orders               (o)   all orders
  riders               (r)   rider event log
  map                  (m)   show map
  tick [n]             (t)   advance n ticks
  history              (hist) command history
  save                 (sv)  save state to JSON
  help                 (h)
  quit / exit          (q)
Each command entered advances the simulation by one tick."""


class Application:
    """Main loop and command handlers."""

    def __init__(self, config_path=None):
        self.system = SystemManager(config_path=config_path)
        self.display = DisplayManager()
        self.input = InputManager()

    def cmd_start(self, args):
        if not args:
            try:
                args = input("Enter restaurant_x restaurant_y customer_x "
                             "customer_y: ").split()
            except EOFError:
                return
        ok, res = self.input.validate_coordinates(args)
        if not ok:
            print("Error:", res)
            return
        om = self.system.order_manager
        order = om.create_order(res)
        print("Order %d created." % order.id)
        print("  Restaurant grid: %s -> center %s" % (order.res_grid,
                                                       order.res_pos))
        print("  Customer   grid: %s -> center %s" % (order.cus_grid,
                                                       order.cus_pos))
        new_rider = self.system.recruit_if_possible()
        print("  New rider added: %s" % (
            "yes (rider %d)" % new_rider.rider_id if new_rider else "no"))
        start_pos = None
        rider = None
        from order import find_best_rider_for_order
        best = find_best_rider_for_order(order)
        if best is not None:
            start_pos = best.queue_end_position()
            rider = om.assign_order(order)
        if rider is None:
            print("  No rider available; order is pending.")
            return
        path = PathPlanner.find_multi_path(start_pos,
                                           [order.res_pos, order.cus_pos])
        dist = PathPlanner.path_length(start_pos, path)
        print("  Assigned to rider %d (speed %d units/tick)" % (
            rider.rider_id, rider.speed))
        print("  Route distance: %d, estimated time: %d ticks" % (
            dist, math.ceil(dist / rider.speed) if rider.speed else 0))
        print(self.display.render_map(self.system.riders, [order],
                                      start_pos, path))

    def handle(self, cmd, args):
        """Dispatch one command; returns False to stop."""
        if cmd == "quit":
            path = self.system.save_state()
            if path:
                print("State saved to %s" % path)
            self.system.stop()
            print("Bye.")
            return False
        if cmd == "start":
            self.cmd_start(args)
        elif cmd == "status":
            print(self.display.render_status(self.system.funds,
                                             self.system.time,
                                             self.system.riders))
        elif cmd == "orders":
            print(self.display.render_orders(
                self.system.order_manager.all_orders()))
        elif cmd == "riders":
            print(self.display.render_rider_logs(self.system.riders))
        elif cmd == "map":
            print(self.display.render_map(
                self.system.riders, self.system.order_manager.all_orders()))
        elif cmd == "tick":
            n = self.input.validate_positive_int(args[0] if args else 1)
            self.system.tick(n - 1)
            print("Advanced %d tick(s)." % n)
        elif cmd == "history":
            for i, h in enumerate(self.input.history, 1):
                print("%4d  %s" % (i, h))
        elif cmd == "save":
            path = self.system.save_state()
            print("Saved to %s" % path if path else "Save failed.")
        elif cmd == "help":
            print(HELP)
        return True

    def run(self):
        """Main loop: each iteration is one tick."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.running:
            try:
                line = input("[t=%d funds=%d]> " % (self.system.time,
                                                    self.system.funds))
            except (EOFError, KeyboardInterrupt):
                print()
                self.handle("quit", [])
                break
            cmd, args = self.input.parse_command(line)
            if cmd is None:
                continue
            if cmd not in COMMANDS:
                print("Unknown command '%s'. Type 'help'." % cmd)
                continue
            try:
                if not self.handle(cmd, args):
                    break
            except Exception as exc:  # graceful recovery
                logging.exception("Command failed")
                print("Error: %s (state recovered)" % exc)
                self.system.check_consistency()
            self.system.tick(1)


def main(argv=None):
    """Program entry."""
    argv = sys.argv[1:] if argv is None else argv
    level = logging.DEBUG if "--debug" in argv else logging.WARNING
    logging.basicConfig(level=level,
                        format="%(levelname)s %(name)s: %(message)s")
    cfg = None
    if "--config" in argv:
        i = argv.index("--config")
        if i + 1 < len(argv):
            cfg = argv[i + 1]
    Application(cfg).run()


if __name__ == "__main__":
    main()
