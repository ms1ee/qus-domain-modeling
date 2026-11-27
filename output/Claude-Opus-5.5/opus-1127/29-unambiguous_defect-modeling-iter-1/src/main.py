"""Command-line entry point for the food delivery dispatch simulator."""

import logging
import os
import sys

import config
import globalvar
import system
from display import DisplayManager
from input_manager import InputManager, InputError
from order import OrderManager

logger = logging.getLogger("dispatch")


class Application:
    """Main loop: each iteration represents one tick of simulated time."""

    def __init__(self, config_path=config.DEFAULT_CONFIG_PATH, input_func=input,
                 output=print):
        self.cfg = config.load_config(config_path)
        self.system = system.init_system(self.cfg)
        self.order_manager = OrderManager()
        self.display = DisplayManager()
        self.input = InputManager(input_func)
        self.out = output

    def handle(self, line):
        """Handle one command line. Returns True if a tick should elapse."""
        cmd, args = self.input.parse_command(line)
        if cmd is None:
            return True
        if cmd == "unknown":
            self.out("Unknown command '%s'. Type 'help' for commands." % args[0])
            return True
        if cmd == "quit":
            self.system.stop()
            return False
        if cmd == "help":
            self.out(self.display.help_text())
        elif cmd == "start":
            text = args if args else self.input.read_raw(
                "Enter restaurant_x restaurant_y customer_x customer_y (0-800): ")
            values = self.input.parse_order_input(text)
            result = self.order_manager.dispatch(values)
            self.out(self.display.format_dispatch(result))
        elif cmd == "status":
            self.out(self.display.format_status())
        elif cmd == "orders":
            self.out(self.display.format_orders(self.order_manager.all_orders()))
        elif cmd == "riders":
            self.out(self.display.format_rider_logs())
        elif cmd == "map":
            self.out(self.display.render_map(None, self.order_manager.active_orders()))
        elif cmd == "history":
            for i, h in enumerate(self.input.command_history, 1):
                self.out("%4d  %s" % (i, h))
        elif cmd == "save":
            path = args[0] if args else self.cfg.get("state_file")
            ok = config.save_state(path)
            self.out("State saved to %s." % path if ok else "Saving failed.")
        elif cmd == "step":
            n = self.input.parse_positive_int(args[0] if args else None)
            self.system.advance(n)
            self.out("Advanced %d tick(s). Now at tick %d."
                     % (n, self.system.current_tick))
            return False
        return True

    def run(self):
        self.out("Food Delivery Dispatch Simulator - type 'help' for commands.")
        while self.system.running:
            try:
                line = self.input.read_command()
            except (EOFError, KeyboardInterrupt):
                self.out("")
                self.system.stop()
                break
            try:
                tick = self.handle(line)
            except InputError as exc:
                self.out("Input error: %s" % exc)
                tick = False
            except Exception as exc:  # recovery: keep running
                logger.exception("Unexpected error")
                self.out("Error: %s (system state recovered)" % exc)
                system.check_consistency()
                tick = False
            if tick and self.system.running:
                self.system.advance(1)
        config.save_state(self.cfg.get("state_file"))
        self.out("Goodbye.")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    level = logging.DEBUG if "--debug" in argv else getattr(
        logging, os.environ.get("DISPATCH_LOG_LEVEL", "WARNING").upper(),
        logging.WARNING)
    logging.basicConfig(level=level,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg_path = config.DEFAULT_CONFIG_PATH
    if "--config" in argv:
        idx = argv.index("--config")
        if idx + 1 < len(argv):
            cfg_path = argv[idx + 1]
    Application(cfg_path).run()
    globalvar.set_value("running", False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
