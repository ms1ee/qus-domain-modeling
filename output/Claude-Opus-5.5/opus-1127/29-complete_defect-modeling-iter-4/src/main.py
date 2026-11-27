"""Command-line entry point for the Food Delivery Order Dispatch System."""

import logging
import sys

import globalvar
from display import DisplayManager
from input_manager import InputManager
from system import init_system


class Application:
    """Main loop: each loop iteration represents one tick."""

    def __init__(self, config_path=None):
        self.system = init_system(config_path)
        level = getattr(logging, str(globalvar.get_value("log_level",
                                                         "WARNING")).upper(),
                        logging.WARNING)
        logging.basicConfig(level=level,
                            format="%(levelname)s %(name)s: %(message)s")
        self.display = DisplayManager()
        self.inputs = InputManager()

    def handle(self, name, args):
        """Execute a command. Returns True if a tick should be advanced."""
        if name == "":
            return True
        if name is None:
            print("Unknown command '{}'. Type 'help' for a list.".format(args[0]))
            return False
        if name in ("quit", "exit"):
            self.system.stop()
            path = self.system.save()
            if path:
                print("State saved to {}".format(path))
            print("Bye.")
            return False
        if name == "help":
            print(self.inputs.help_text())
            return False
        if name == "history":
            for i, cmd in enumerate(self.inputs.command_history, 1):
                print("{:>4}  {}".format(i, cmd))
            return False
        if name == "start":
            if not args:
                line = self.inputs.read_line(
                    "restaurant_x restaurant_y customer_x customer_y: ")
                args = line
            try:
                coords = self.inputs.validate_coordinates(args)
            except ValueError as exc:
                print("Invalid input: {}".format(exc))
                return False
            result = self.system.place_order(coords)
            print(self.display.format_start_result(result))
            return True
        if name == "status":
            print(self.display.format_status())
            return True
        if name == "map":
            print(self.display.render_grid())
            return True
        if name == "orders":
            print(self.display.format_orders())
            return True
        if name == "riders":
            print(self.display.format_rider_logs())
            return True
        if name == "tick":
            count = 1
            if args:
                try:
                    count = int(args[0])
                except ValueError:
                    print("Invalid tick count '{}'".format(args[0]))
                    return False
                if count < 1 or count > 10000:
                    print("Tick count must be 1-10000")
                    return False
            self.system.advance_tick(count)
            print("Advanced {} tick(s); now at tick {}.".format(
                count, self.system.current_tick))
            return False
        if name == "save":
            path = self.system.save()
            print("Saved to {}".format(path) if path else "Save failed.")
            return False
        return False

    def run(self):
        print("Food Delivery Order Dispatch System (8x8 grid, 800x800)")
        print(self.inputs.help_text())
        while self.system.running:
            line = self.inputs.read_line("[t={} funds={}]> ".format(
                self.system.current_tick, self.system.funds))
            try:
                name, args = self.inputs.parse(line)
                if self.handle(name, args) and self.system.running:
                    self.system.advance_tick(1)
            except ValueError as exc:
                print("Error: {}".format(exc))
            except Exception as exc:  # recovery
                logging.getLogger(__name__).exception("Unexpected error")
                print("Unexpected error: {} - recovering.".format(exc))
                self.system.check_consistency()
        return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    config_path = argv[0] if argv else None
    return Application(config_path).run()


if __name__ == "__main__":
    sys.exit(main())
