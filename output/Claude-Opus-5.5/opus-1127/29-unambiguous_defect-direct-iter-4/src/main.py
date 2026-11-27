"""Command-line entry point of the food delivery dispatch simulator.

Every loop iteration of the main program is one simulated tick: each
command (or an empty Enter) advances time by one tick, except 'tick',
'run', 'help', 'history', 'save' and 'quit'.
"""

import argparse
import logging
import sys

import globalvar
from system import init_system
from order import OrderManager
from display import DisplayManager
from input_manager import InputManager

logger = logging.getLogger("dispatch")

HELP = """Commands (shortcut in brackets):
  start [s]   rx ry cx cy   create an order (coordinates 0-800); prompts if omitted
  status [st]               funds, riders, orders and map
  orders [o]                details of all orders
  riders [r]                rider status-change log
  map [m]                   ASCII map
  tick [t] [n]              advance n ticks (default 1)
  run                       advance until all orders are delivered
  history [hist]            command history ('!!' repeats last command)
  save                      save state to JSON
  help [h, ?]               this help
  quit / exit [q]           leave the program
Pressing Enter advances the clock by one tick."""

NO_TICK = {"tick", "run", "help", "history", "save", "quit"}


class DispatchApp:
    """Ties the managers together and runs the command loop."""

    def __init__(self, config_path=None):
        self.system = init_system(config_path)
        self.order_manager = OrderManager(self.system)
        self.display = DisplayManager(self.system)
        self.input = InputManager()

    def handle(self, line):
        """Execute one command line. Returns True if the loop should tick."""
        cmd, args = self.input.parse_command(line)
        if cmd == "":
            return True
        if cmd == "start":
            if not args:
                raw = self.input.read("Enter restaurant_x restaurant_y customer_x customer_y: ")
                args = raw
            result = self.order_manager.place_order(args)
            print(self.display.order_result_text(result))
        elif cmd == "status":
            print(self.display.status_text())
        elif cmd == "orders":
            print(self.display.orders_text())
        elif cmd == "riders":
            print(self.display.riders_log_text())
        elif cmd == "map":
            print(self.display.render_map())
        elif cmd == "tick":
            n = self.input.parse_positive_int(args[0] if args else None)
            self.system.tick(n)
            print("Advanced %d tick(s). Time is now %d." % (n, self.system.time))
        elif cmd == "run":
            used = self.system.run_until_idle()
            print("Advanced %d tick(s). Time is now %d." % (used, self.system.time))
        elif cmd == "history":
            for i, h in enumerate(self.input.history, 1):
                print("%4d  %s" % (i, h))
        elif cmd == "save":
            path = self.system.save_state()
            print("State saved to %s" % path if path else "Saving failed.")
        elif cmd == "help":
            print(HELP)
        elif cmd == "quit":
            self.system.stop()
            return False
        else:
            print("Unknown command '%s'. Type 'help' for the list of commands." % cmd)
            return False
        return cmd not in NO_TICK

    def run(self):
        """Main loop: one iteration per tick."""
        print("Food Delivery Dispatch Simulator - type 'help' for commands.")
        while globalvar.get_value("running"):
            try:
                line = self.input.read("[t=%d funds=%d] > " % (self.system.time, self.system.funds))
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.stop()
                break
            try:
                advance = self.handle(line)
            except ValueError as exc:
                print("Input error: %s" % exc)
                advance = False
            except (EOFError, KeyboardInterrupt):
                print()
                advance = False
            except Exception as exc:  # recovery
                logger.exception("Command failed")
                print("Error: %s (system state checked and recovered)" % exc)
                self.system.check_consistency()
                advance = False
            if advance and globalvar.get_value("running"):
                self.system.tick()
        self.system.save_state()
        print("Goodbye.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="path to JSON config file")
    parser.add_argument("--debug", action="store_true", help="print debug logs")
    parser.add_argument("--log-file", help="write logs to this file")
    opts = parser.parse_args(argv)
    level = logging.DEBUG if opts.debug else logging.WARNING
    if opts.log_file:
        logging.basicConfig(filename=opts.log_file, level=level,
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    else:
        logging.basicConfig(stream=sys.stderr, level=level,
                            format="%(levelname)s %(name)s: %(message)s")
    DispatchApp(opts.config).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
