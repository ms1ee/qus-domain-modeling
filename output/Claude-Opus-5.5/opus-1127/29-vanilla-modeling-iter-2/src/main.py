"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys

import globalvar
import system
from config import load_config
from display import DisplayManager
from grid_map import cell_index
from input_manager import COMMANDS, InputError, InputManager
from order import OrderManager
import persistence

HELP = """Commands (shortcut):
  start (s) [rx ry cx cy]  Create an order (coordinates 0-800)
  status (st)              Show funds and rider states
  orders (o)               Show all orders
  riders (r)               Show rider status change logs
  map (m)                  Show the current map
  tick (t) [n]             Advance simulation by n ticks (default 1)
  save [file] / load [file] Persist / restore state (default state.json)
  history (hist)           Show command history
  help (h, ?)              Show this help
  quit / exit (q)          Exit
Each command also advances simulated time by one tick."""


class Application:
    """Main interactive application."""

    def __init__(self, config=None, out=None):
        system.init_system(config)
        self.inputs = InputManager()
        self.display = DisplayManager()
        self.orders = OrderManager()
        self.out = out or sys.stdout

    def write(self, text=""):
        self.out.write(str(text) + "\n")

    def handle(self, line, read=input):
        """Process one command line. Returns False when quitting."""
        cmd, args = self.inputs.parse_command(line)
        if not cmd:
            return True
        if cmd not in COMMANDS:
            self.write("Unknown command '%s'. Type 'help'." % cmd)
            return True
        try:
            if cmd == "quit":
                globalvar.set_value("running", False)
                self.write("Goodbye.")
                return False
            if cmd == "start":
                if not args.strip():
                    args = read("Enter restaurant_x restaurant_y customer_x customer_y: ")
                self.cmd_start(self.inputs.parse_coordinates(args))
            elif cmd == "status":
                self.write(self.display.render_status())
            elif cmd == "orders":
                self.write(self.display.render_orders())
            elif cmd == "riders":
                self.write(self.display.render_rider_logs())
            elif cmd == "map":
                self.write(self.display.render_map())
            elif cmd == "tick":
                n = self.inputs.parse_positive_int(args)
                system.advance_tick(n - 1)  # main loop adds one more tick
                self.write("Advancing %d tick(s)." % n)
            elif cmd == "save":
                path = args.strip() or "state.json"
                persistence.save_state(path)
                self.write("State saved to %s" % path)
            elif cmd == "load":
                path = args.strip() or "state.json"
                persistence.load_state(path)
                system.validate_state()
                self.write("State loaded from %s" % path)
            elif cmd == "history":
                for i, h in enumerate(self.inputs.command_history, 1):
                    self.write("%4d  %s" % (i, h))
            elif cmd == "help":
                self.write(HELP)
        except InputError as exc:
            self.write("Input error: %s" % exc)
        except (OSError, ValueError, KeyError) as exc:
            self.write("Error: %s" % exc)
        except Exception as exc:  # graceful recovery
            logging.exception("Unexpected error")
            self.write("Unexpected error: %s (state checked and recovered)" % exc)
            system.validate_state()
        return True

    def cmd_start(self, coords):
        """Create an order and print the dispatch result."""
        order, rider, recruited = self.orders.create_order(coords)
        self.write("Order #%d created." % order.id)
        self.write("Restaurant grid point: (%d,%d) cell (%d,%d)" % (
            order.res_x, order.res_y, cell_index(order.res_x), cell_index(order.res_y)))
        self.write("Customer grid point:   (%d,%d) cell (%d,%d)" % (
            order.cus_x, order.cus_y, cell_index(order.cus_x), cell_index(order.cus_y)))
        if recruited:
            self.write("New rider added: Yes (%s), funds now %s" % (
                ", ".join("#%s" % r.rider_id for r in recruited),
                globalvar.get_value("funds")))
        else:
            self.write("New rider added: No")
        if rider is None:
            self.write("No rider available; order is pending.")
            return
        self.write("Assigned to rider #%s" % rider.rider_id)
        self.write(self.display.render_route(rider))

    def run(self):
        """Run the main loop; each iteration is one tick."""
        self.write("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while globalvar.get_value("running", False):
            try:
                line = input("[t=%s] > " % globalvar.get_value("current_tick", 0))
            except (EOFError, KeyboardInterrupt):
                self.write("\nExiting.")
                globalvar.set_value("running", False)
                break
            if not self.handle(line):
                break
            system.advance_tick(1)


def main(argv=None):
    """Program entry point."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="JSON configuration file")
    parser.add_argument("--load", help="Load saved state JSON")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = Application(load_config(args.config))
    if args.load:
        try:
            persistence.load_state(args.load)
        except (OSError, ValueError, KeyError) as exc:
            print("Could not load state: %s" % exc)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
