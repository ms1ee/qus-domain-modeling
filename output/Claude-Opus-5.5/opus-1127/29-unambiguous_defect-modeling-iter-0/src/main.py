"""Command line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import globalvar  # noqa: E402
import system  # noqa: E402
from config import Configuration, save_state, load_state  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402
from order import OrderManager  # noqa: E402

logger = logging.getLogger("dispatch")

NO_TICK_COMMANDS = ("help", "history", "quit", "save", "load", "tick", "run",
                    None, "unknown", "error")


class Application:
    """Main interactive loop; every command iteration is a time step."""

    def __init__(self, config_path="config.json", input_func=input, out=None):
        self.out = out or sys.stdout
        self.config = Configuration(config_path)
        self.manager = system.SystemManager(self.config.load())
        self.inputs = InputManager(input_func)

    def write(self, text=""):
        self.out.write(text + "\n")

    def run(self):
        self.write("Food Delivery Dispatch Simulator - type 'help' for commands.")
        while globalvar.get_value("running", False):
            line = self.inputs.read_line("[t=%s] > " % globalvar.get_value("tick", 0))
            self.handle(line)

    def handle(self, line):
        """Process a single command line."""
        cmd, args = self.inputs.parse(line)
        try:
            self.dispatch(cmd, args)
            if cmd not in NO_TICK_COMMANDS:
                system.advance_tick(globalvar.get_value("ticks_per_command", 1))
        except ValueError as exc:
            self.write("Error: %s" % exc)
        except Exception as exc:  # recovery
            logger.exception("Unexpected error")
            self.write("Unexpected error: %s. Recovering state..." % exc)
            fixes = system.check_consistency()
            if fixes:
                self.write("Repaired: " + "; ".join(fixes))

    def dispatch(self, cmd, args):
        if cmd is None:
            return
        if cmd == "unknown":
            self.write("Unknown command '%s'. Type 'help'." % args[0])
        elif cmd == "error":
            self.write("Error: %s" % args[0])
        elif cmd == "help":
            self.write(InputManager.help_text())
        elif cmd == "history":
            self.write(self.inputs.history_text())
        elif cmd == "quit":
            globalvar.set_value("running", False)
            self.write("Goodbye.")
        elif cmd == "start":
            self.cmd_start(args)
        elif cmd == "status":
            self.write(DisplayManager.status_text())
        elif cmd == "orders":
            self.write(DisplayManager.orders_text())
        elif cmd == "riders":
            self.write(DisplayManager.riders_log_text())
        elif cmd == "map":
            self.write(DisplayManager.render_map())
        elif cmd == "tick":
            n = InputManager.parse_positive_int(args)
            system.advance_tick(n)
            self.write("Advanced %d tick(s). Now t=%s." % (n, globalvar.get_value("tick")))
        elif cmd == "run":
            used = self.manager.run_until_idle()
            self.write("Ran %d tick(s); all orders delivered: %s." % (
                used, system.all_idle()))
        elif cmd == "save":
            path = args[0] if args else "state.json"
            save_state(path)
            self.write("State saved to %s." % path)
        elif cmd == "load":
            path = args[0] if args else "state.json"
            load_state(path)
            system.check_consistency()
            self.write("State loaded from %s." % path)

    def cmd_start(self, args):
        if not args:
            line = self.inputs.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y (0-800): ")
            args = line.replace(",", " ").replace("[", " ").replace("]", " ").split()
        coords = InputManager.parse_coordinates(args)
        order = OrderManager.create_order(coords)
        rider, recruited = OrderManager.assign_order(order)
        self.write(DisplayManager.order_assignment_text(order, rider, recruited))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default="config.json", help="JSON config file")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    opts = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if opts.debug else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    Application(opts.config).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
