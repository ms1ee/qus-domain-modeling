"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import os
import sys

import globalvar
from config import Configuration
from display import DisplayManager
from input_manager import HELP_TEXT, InputManager
from system import init_system

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

logger = logging.getLogger("dispatch")


class Application:
    """Main loop: each iteration is one simulated tick."""

    def __init__(self, config_path=None, load_path=None):
        config = Configuration(config_path if config_path and
                               os.path.exists(config_path) else None)
        globalvar._init()
        self.system = init_system(config)
        self.display = DisplayManager(self.system)
        self.inputs = InputManager()
        if load_path:
            self.system.load_state(load_path)
            print("State loaded from %s" % load_path)

    def _start(self, args):
        text = " ".join(args) if args else input(
            "Enter restaurant_x restaurant_y customer_x customer_y (0-800): ")
        coords = self.inputs.parse_coordinates(text)
        result = self.system.place_order(coords)
        print(self.display.start_report(result))
        return 1

    def handle(self, line):
        """Execute one command line; returns number of ticks to advance."""
        cmd, args = self.inputs.parse(line)
        if cmd is None:
            return 1
        if cmd == "start":
            return self._start(args)
        if cmd == "status":
            print(self.display.status_text())
        elif cmd == "orders":
            print(self.display.orders_text())
        elif cmd == "riders":
            print(self.display.riders_text())
        elif cmd == "map":
            print(self.display.render_map())
        elif cmd == "tick":
            return self.inputs.parse_count(args)
        elif cmd == "help":
            print(HELP_TEXT)
        elif cmd == "history":
            print(self.inputs.history_text())
        elif cmd == "check":
            issues = self.system.check_consistency(repair=True)
            print("System consistent." if not issues
                  else "Repaired: " + "; ".join(issues))
        elif cmd == "save":
            print("Saved to %s" % self.system.save_state(
                args[0] if args else None))
        elif cmd == "load":
            print("Loaded from %s" % self.system.load_state(
                args[0] if args else None))
            return 0
        elif cmd == "quit":
            self.system.running = False
            return 0
        return 1

    def run(self):
        print("Food Delivery Order Dispatch Simulator (8x8 grid, 800x800)")
        print(HELP_TEXT)
        if not self.system.riders:
            rider = self.system.recruit_if_possible()
            if rider:
                print("Rider #%d recruited (funds now %d)"
                      % (rider.rider_id, self.system.funds))
        while self.system.running:
            try:
                line = input("[t=%d funds=%d] > " % (self.system.current_time,
                                                     self.system.funds))
            except (EOFError, KeyboardInterrupt):
                print()
                line = "quit"
            try:
                ticks = self.handle(line)
            except ValueError as exc:
                print("Error: %s" % exc)
                ticks = 0
            except (OSError, KeyError) as exc:
                print("Error: %s" % exc)
                ticks = 0
            except Exception as exc:  # recovery mechanism
                logger.exception("Unexpected error")
                print("Unexpected error: %s (system state repaired)" % exc)
                self.system.check_consistency(repair=True)
                ticks = 0
            if self.system.running and ticks:
                for event in self.system.tick(ticks):
                    print("  " + event)
        print("Goodbye.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json",
                        help="JSON configuration file")
    parser.add_argument("--load", default=None, help="load saved state")
    parser.add_argument("--debug", action="store_true", help="debug logging")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    Application(args.config, args.load).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
