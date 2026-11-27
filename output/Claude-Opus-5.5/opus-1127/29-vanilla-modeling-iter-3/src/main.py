"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import os
import sys

import globalvar
import system
from display import DisplayManager
from input_manager import HELP_TEXT, InputManager
from order import OrderManager

DEFAULT_SAVE = "state.json"


class Application:
    """Main interactive loop; each iteration is one simulated tick."""

    def __init__(self, config=None):
        self.orders = OrderManager()
        self.system = system.SystemManager(config, self.orders)
        self.display = DisplayManager()
        self.input = InputManager()

    def handle(self, line):
        """Handle one line of input; returns True if a tick should elapse."""
        cmd, rest = self.input.parse(line)
        if cmd == "":
            return True
        if cmd == "quit":
            self.system.stop()
            print("Bye.")
            return False
        if cmd == "start":
            self.cmd_start(rest)
        elif cmd == "status":
            print(self.display.status_text())
        elif cmd == "orders":
            print(self.display.orders_text())
        elif cmd == "riders":
            rid = int(rest) if rest.strip() else None
            print(self.display.riders_text(rid))
        elif cmd == "map":
            print(self.display.render_map())
        elif cmd == "run":
            n = self.input.parse_positive_int(rest, 1)
            self.system.advance(n - 1)
            print("Advanced to tick %d." % (self.system.current_tick + 1))
        elif cmd == "save":
            path = rest.strip() or DEFAULT_SAVE
            self.system.save(path)
            print("State saved to %s." % path)
            return False
        elif cmd == "load":
            path = rest.strip() or DEFAULT_SAVE
            self.system.load(path)
            print("State loaded from %s." % path)
            return False
        elif cmd == "history":
            for i, h in enumerate(self.input.command_history, 1):
                print("%3d  %s" % (i, h))
        elif cmd == "help":
            print(HELP_TEXT)
        else:
            print("Unknown command '%s'. Type 'help' for a list." % cmd)
            return False
        return True

    def cmd_start(self, rest):
        if not rest.strip():
            rest = input("Enter [restaurant_x, restaurant_y, customer_x, customer_y]: ")
        coords = self.input.parse_coordinates(rest)
        result = self.orders.place_order(coords)
        order = result["order"]
        print("Order #%d created." % order.id)
        print("Restaurant grid position: (%d, %d)" % order.res_pos)
        print("Customer grid position  : (%d, %d)" % order.cus_pos)
        print("New rider added: %s" % ("yes" if result["recruited"] else "no"))
        rider = result["rider"]
        if rider is None:
            print("No rider available; order is pending (funds: %s)."
                  % self.system.funds)
            return
        route = result["route"]
        print("Assigned to rider %d at (%d, %d)." % (rider.rider_id, rider.x, rider.y))
        print("Speed: %d units/tick, route length: %d, estimated time: %d ticks"
              % (route.speed, route.length, route.estimated_time))
        print(self.display.render_map(route))

    def run(self):
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.running:
            try:
                line = input("[t=%d] > " % self.system.current_tick)
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.stop()
                break
            advance = False
            try:
                advance = self.handle(line)
            except ValueError as exc:
                print("Input error: %s" % exc)
            except (OSError, KeyError) as exc:
                print("Error: %s" % exc)
            except Exception as exc:  # pragma: no cover - recovery
                logging.exception("Unexpected error")
                print("Unexpected error: %s (system state preserved)" % exc)
            if advance and self.system.running:
                self.system.advance(1)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "config.json"))
    parser.add_argument("--load", default=None, help="load saved state JSON")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    config = system.load_config(args.config)
    app = Application(config)
    if args.load:
        try:
            system.load_state(args.load)
        except (OSError, ValueError, KeyError) as exc:
            print("Could not load state: %s" % exc)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
