"""Command line entry point of the food delivery dispatch simulator."""

import logging
import os
import sys

import globalvar
from config import load_config
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from system import SystemManager, init_system

HELP = """Commands (shortcut in brackets):
  start [rx ry cx cy] (s)  create an order: restaurant + customer coords 0-800
  status (st)              system funds and rider states
  orders (o)               all orders
  riders (r)               rider status change history
  map (m)                  ASCII map
  tick [n] (t)             advance the simulation n ticks
  history (hist)           command history
  save (sv)                save state to JSON
  help (h)                 this help
  quit / exit (q)          exit the program
Every command advances the simulation by one tick."""


class Application:
    """Main application loop."""

    def __init__(self, config=None):
        globalvar._init()
        init_system(config)
        self.system = SystemManager()
        self.orders = OrderManager(self.system)
        self.display = DisplayManager()
        self.input = InputManager()

    def handle(self, cmd, args):
        """Handle one command; returns False if the clock must not tick."""
        if cmd == "":
            return True
        if cmd == "start":
            if not args:
                args = [self.input.read(
                    "Enter restaurant_x restaurant_y customer_x customer_y: ")]
            coords = self.input.parse_coordinates(args)
            result = self.orders.create_order(coords)
            print(self.display.order_result_text(result))
        elif cmd == "status":
            print(self.display.status_text())
        elif cmd == "orders":
            print(self.display.orders_text())
        elif cmd == "riders":
            print(self.display.riders_text())
        elif cmd == "map":
            print(self.display.render_map())
        elif cmd == "tick":
            n = self.input.parse_positive_int(args)
            self.system.tick(n)
            print("Advanced %d tick(s); time is now %s."
                  % (n, self.system.time))
            return False
        elif cmd == "history":
            for i, line in enumerate(self.input.history, 1):
                print("%4d  %s" % (i, line))
        elif cmd == "save":
            path = self.system.save_state()
            print("State saved to %s" % path if path else "Save failed.")
        elif cmd == "help":
            print(HELP)
        elif cmd == "quit":
            self.system.stop()
            return False
        else:
            print("Unknown command '%s'. Type 'help' for commands." % cmd)
            return False
        return True

    def run(self):
        """Run the interactive loop."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands.")
        while self.system.running:
            try:
                line = self.input.read("[t=%s] > " % self.system.time)
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.stop()
                break
            cmd, args = self.input.parse_command(line)
            try:
                if self.handle(cmd, args):
                    self.system.tick(1)
            except ValueError as exc:
                print("Input error: %s" % exc)
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.stop()
            except Exception as exc:  # graceful recovery
                logging.getLogger(__name__).exception("Unexpected error")
                print("Error: %s (system state recovered)" % exc)
                self.system.check_consistency()
        path = self.system.save_state()
        if path:
            print("State saved to %s" % path)
        print("Goodbye.")


def main(argv=None):
    """Program entry point."""
    argv = sys.argv[1:] if argv is None else argv
    level = logging.DEBUG if "--debug" in argv else logging.WARNING
    logging.basicConfig(level=level,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg_path = "config.json"
    for i, a in enumerate(argv):
        if a == "--config" and i + 1 < len(argv):
            cfg_path = argv[i + 1]
    if not os.path.isfile(cfg_path):
        alt = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "config.json")
        cfg_path = alt
    Application(load_config(cfg_path)).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
