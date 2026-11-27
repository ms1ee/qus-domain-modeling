"""Command-line entry point of the Food Delivery Order Dispatch simulator."""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Configuration  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402
from order import OrderManager  # noqa: E402
from system import SystemManager, init_system  # noqa: E402

logger = logging.getLogger("dispatch")


class Application:
    """Main loop: each iteration represents one tick of simulated time."""

    def __init__(self, config_path=None, autosave=None):
        self.configuration = Configuration(config_path)
        init_system(self.configuration.data)
        self.system = SystemManager()
        self.order_manager = OrderManager(self.system)
        self.display = DisplayManager(self.system)
        self.input = InputManager()
        self.autosave = (self.configuration.get("autosave", True)
                         if autosave is None else autosave)

    def handle(self, line):
        """Handle one command line. Returns True if a tick should follow."""
        command, args = self.input.parse(line)
        if command == "":
            return True
        if command == "quit":
            self.system.running = False
            return False
        if command == "help":
            print(self.display.help_text())
        elif command == "start":
            self._start(args)
        elif command == "status":
            print(self.display.format_status())
        elif command == "orders":
            print(self.display.format_orders())
            stats = self.order_manager.statistics()
            print(f"Total {stats['total']}, completed {stats['completed']}, active "
                  f"{stats['active']}, avg time {stats['average_time']}, avg efficiency "
                  f"{stats['average_efficiency']} units/tick")
        elif command == "riders":
            print(self.display.format_rider_logs())
        elif command == "map":
            print(self.display.render_map())
        elif command == "history":
            for i, item in enumerate(self.input.command_history, 1):
                print(f"{i:>4}  {item}")
        elif command == "save":
            path = self.configuration.get("state_file", "dispatch_state.json")
            ok = self.system.save_state(path)
            print(f"State saved to {path}" if ok else "Saving failed.")
        elif command == "tick":
            try:
                n = self.input.parse_positive_int(args[0] if args else None)
            except ValueError as exc:
                print(f"Error: {exc}")
                return False
            self._advance(n)
            return False
        elif command == "run":
            ticks = 0
            while self.system.has_pending_work() and ticks < 10000:
                self._advance(1)
                ticks += 1
            print(f"Ran {ticks} tick(s); all orders delivered."
                  if not self.system.has_pending_work() else "Stopped after 10000 ticks.")
            return False
        else:
            print(f"Unknown command '{args[0] if args else ''}'. Type 'help'.")
        return True

    def _start(self, args):
        try:
            if args:
                coords = self.input.parse_coordinates(args)
            else:
                text = input("Enter restaurant_x restaurant_y customer_x customer_y: ")
                coords = self.input.parse_coordinates(text)
        except ValueError as exc:
            print(f"Invalid input: {exc}")
            return
        try:
            result = self.order_manager.place_order(coords)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Order placement failed")
            print(f"Error placing order: {exc}")
            self.system.check_consistency()
            return
        print(self.display.format_order_result(result))

    def _advance(self, n):
        events = self.system.tick(n)
        if events:
            print(self.display.format_events(events))

    def run(self):
        """Run the interactive main loop."""
        print("Food Delivery Order Dispatch System")
        print(f"Funds: {self.system.funds}. Type 'help' for commands.")
        while self.system.running:
            try:
                line = self.input.read_command(f"[t={self.system.current_time}] > ")
            except (EOFError, KeyboardInterrupt):
                print()
                line = "quit"
            try:
                advance = self.handle(line)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Unexpected error")
                print(f"Unexpected error: {exc}; recovering.")
                self.system.check_consistency()
                advance = False
            if advance and self.system.running:
                self._advance(1)
        if self.autosave:
            path = self.configuration.get("state_file", "dispatch_state.json")
            if self.system.save_state(path):
                print(f"State saved to {path}")
        print("Goodbye.")


def main(argv=None):
    """Program entry point."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    default_cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    parser.add_argument("--config", default=default_cfg, help="JSON config file")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    parser.add_argument("--no-save", action="store_true", help="do not save state on exit")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    app = Application(args.config, autosave=False if args.no_save else None)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
