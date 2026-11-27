"""Command-line entry point for the Food Delivery Order Dispatch System.

Run with ``python src/main.py`` (or ``python -m src.main`` from the project
root). The main loop reads commands; simulated time advances through the
``start`` and ``tick`` commands, one tick per unit of time.
"""

import logging
import os
import sys

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from config import load_config  # noqa: E402
from display import DisplayManager  # noqa: E402
from grid import MAX_COORDINATE, MIN_COORDINATE  # noqa: E402
from input_manager import InputManager  # noqa: E402
from order_model import Order  # noqa: E402
from system import init_system  # noqa: E402

logger = logging.getLogger("dispatch")

BANNER = ("Food Delivery Order Dispatch System\n"
          "Type 'help' for commands, 'quit' to exit.")


def setup_logging(config):
    """Configure file logging from the configuration.

    Falls back to warnings on stderr if the log file cannot be opened.

    Args:
        config: System configuration dictionary.
    """
    level = getattr(logging, str(config.get("log_level", "INFO")).upper(),
                    logging.INFO)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    try:
        logging.basicConfig(filename=config["log_file"], level=level,
                            format=fmt)
    except (OSError, ValueError):
        logging.basicConfig(level=logging.WARNING, format=fmt)


class Application:
    """Interactive command loop wiring the managers together."""

    def __init__(self, config, input_func=input, output_func=print):
        """Initialise the system and the interface components.

        Args:
            config: System configuration dictionary.
            input_func: Function used to read input (injectable).
            output_func: Function used to print output (injectable).
        """
        self.config = config
        self.out = output_func
        self.system = init_system(config)
        self.display = DisplayManager()
        self.cli = InputManager(MIN_COORDINATE, MAX_COORDINATE,
                                input_func=input_func,
                                output_func=output_func)
        self._handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "history": self.cmd_history,
            "save": self.cmd_save,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }

    def run(self):
        """Run the main loop until the user quits or input ends."""
        self.out(BANNER)
        while self.system.is_running:
            try:
                line = self.cli.read_command()
            except (EOFError, KeyboardInterrupt):
                self.out("")
                self.system.shutdown(str(self.config["save_file"]))
                break
            except ValueError as exc:
                self.out(f"Error: {exc}")
                continue
            if not line:
                continue
            try:
                name, args = self.cli.parse_command(line)
                self._handlers[name](args)
            except ValueError as exc:
                self.out(f"Error: {exc}")
            except Exception:  # keep the session alive on unexpected errors
                logger.exception("Unexpected error handling '%s'", line)
                self.out("Unexpected internal error; state preserved. "
                         "See the log file for details.")
        self.out("Goodbye.")

    def cmd_start(self, args):
        """Place an order, run it to completion and show the route."""
        coords = self.cli.parse_coordinates(args)
        restaurant = (coords[0], coords[1])
        customer = (coords[2], coords[3])
        order, new_rider, rider = self.system.submit_order(restaurant,
                                                           customer)
        self.out(self.display.format_start_result(order, rider, new_rider))
        self.out(self.display.render_map(self.system.riders, [order],
                                         order.route_points))
        self.out(self.display.legend())
        if order.status != Order.COMPLETED:
            self.out("The order is still pending. Use 'tick' to advance time "
                     "once a rider is available.")

    def cmd_status(self, args):
        """Show funds, rider count and each rider's state and orders."""
        riders = self.system.riders
        self.out(self.display.format_status(self.system, riders))
        self.out(self.display.render_map(
            riders, self.system.order_manager.active_orders()))
        self.out(self.display.legend())

    def cmd_orders(self, args):
        """Show the details of every order."""
        self.out(self.display.format_orders(
            self.system.order_manager.orders))

    def cmd_riders(self, args):
        """Show the status-change log of every rider."""
        self.out(self.display.format_riders(self.system.riders))

    def cmd_map(self, args):
        """Show the ASCII map with riders and active orders."""
        self.out(self.display.render_map(
            self.system.riders, self.system.order_manager.active_orders()))
        self.out(self.display.legend())

    def cmd_tick(self, args):
        """Advance the simulated clock by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(
                    f"tick count must be an integer, got '{args[0]}'") from None
        if not 1 <= count <= 10000:
            raise ValueError("tick count must be between 1 and 10000")
        self.system.run_ticks(count)
        self.out(f"Advanced {count} tick(s). Current tick: "
                 f"{self.system.current_tick}. Funds: {self.system.funds}.")

    def cmd_history(self, args):
        """Print the command history."""
        history = self.cli.command_history
        if not history:
            self.out("No commands yet.")
            return
        for index, command in enumerate(history, start=1):
            self.out(f"{index:>4}  {command}")

    def cmd_save(self, args):
        """Save the system state to a JSON file."""
        path = args[0] if args else None
        if self.system.save(path):
            self.out(f"State saved to {path or self.config['save_file']}.")
        else:
            self.out("Error: could not save state; see the log file.")

    def cmd_help(self, args):
        """Print the command list."""
        self.out(self.cli.help_text())

    def cmd_quit(self, args):
        """Save the state and stop the main loop."""
        self.system.shutdown(str(self.config["save_file"]))
        self.out("Saving state and exiting.")


def main(argv=None):
    """Program entry point.

    Args:
        argv: Unused; reserved for future command-line options.

    Returns:
        Process exit code.
    """
    config = load_config()
    setup_logging(config)
    logger.info("Starting dispatch system")
    app = Application(config)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
