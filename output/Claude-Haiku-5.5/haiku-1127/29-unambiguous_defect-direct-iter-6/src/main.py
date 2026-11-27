"""Command-line entry point for the food delivery dispatch simulator.

Run with ``python src/main.py``. The main loop processes one command per
iteration; every iteration also advances the simulation by one tick.
"""

import argparse
import logging
import math
import sys

import config
import globalvar
from display import DisplayManager
from input_manager import CommandError, InputError, InputManager
from order import NoRiderAvailableError, OrderManager
from order_model import Order
from path_planner import PathPlanner
from system import SystemManager, init_system

logger = logging.getLogger("dispatch")


def setup_logging(log_file, debug=False):
    """Configure logging to a file, plus stderr when debugging.

    Args:
        log_file: Path of the log file.
        debug: If True, log at DEBUG level to stderr as well.
    """
    level = logging.DEBUG if debug else logging.INFO
    handlers = []
    try:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    except OSError as exc:
        sys.stderr.write(f"Warning: cannot open log file {log_file}: {exc}\n")
    if debug:
        handlers.append(logging.StreamHandler(sys.stderr))
    if not handlers:
        handlers.append(logging.NullHandler())
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


class DispatchApp:
    """Interactive command loop tying all modules together."""

    def __init__(self, config_path=None):
        """Initialise the system, managers, and command table.

        Args:
            config_path: Optional path to a JSON configuration file.
        """
        init_system(config_path)
        self.system = SystemManager()
        self.orders = OrderManager(self.system)
        self.display = DisplayManager()
        self.inp = InputManager()
        self._announced = set()
        self.system.bootstrap()
        self.handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "save": self.cmd_save,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }

    def run(self):
        """Run the main loop until the user quits or input closes."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands, 'quit' to exit.")
        print(self.display.format_status(self.system.funds, self.system.tick, self.system.riders))
        while self.system.running:
            try:
                line = self.inp.read_line("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.stop()
                break
            if line:
                self.execute(line)
            if self.system.running:
                self.advance(1)

    def execute(self, line):
        """Parse and run one command, reporting errors without crashing.

        Args:
            line: Raw command line.
        """
        try:
            name, args = self.inp.parse_command(line)
        except CommandError as exc:
            print(self.display.format_error(str(exc)))
            return
        if not name:
            return
        try:
            self.handlers[name](args)
        except (InputError, ValueError) as exc:
            print(self.display.format_error(str(exc)))
        except Exception:
            logger.exception("Unexpected error while running '%s'", name)
            print("Error: unexpected failure; system state has been preserved.")

    def advance(self, steps=1):
        """Advance the simulation by a number of ticks.

        Args:
            steps: Number of ticks to run.
        """
        for _ in range(steps):
            try:
                self.orders.dispatch_pending()
            except Exception:
                logger.exception("Failed to dispatch pending orders")
            self.system.tick()
            self._announce_completions()

    def _announce_completions(self):
        """Print a message for each order delivered since the last check."""
        for order in globalvar.get_value("orders") or []:
            if order.status == Order.STATUS_COMPLETED and order.id not in self._announced:
                self._announced.add(order.id)
                print(
                    f"[tick {self.system.tick}] Order {order.id} delivered by rider "
                    f"{order.rider_id} (time {order.time_taken} ticks, "
                    f"efficiency {order.efficiency})"
                )

    def cmd_start(self, args):
        """Create and assign an order from four coordinates.

        Args:
            args: Optional list of four coordinate tokens.
        """
        if args:
            coords = self.inp.parse_coordinates(args)
        else:
            coords = self.inp.prompt_coordinates()
        order = self.orders.create_order(coords)
        try:
            rider, new_rider, route = self.orders.assign_order(order)
        except NoRiderAvailableError:
            self.orders.queue(order)
            print(
                f"Order {order.id} queued: no rider is free and recruitment is not "
                f"possible (funds {self.system.funds})."
            )
            return
        length = PathPlanner.path_length(route)
        eta = math.ceil(length / rider.speed) if length else 0
        print(self.display.format_start_result(order, rider, new_rider, length, eta))
        print(self.display.render_map(self.system.riders, [order], route))

    def cmd_status(self, args):
        """Print the system status snapshot.

        Args:
            args: Unused.
        """
        print(self.display.format_status(self.system.funds, self.system.tick, self.system.riders))
        if self.orders.pending:
            print(f"Queued orders waiting for a rider: {[o.id for o in self.orders.pending]}")

    def cmd_orders(self, args):
        """Print the table of all orders.

        Args:
            args: Unused.
        """
        print(self.display.format_orders(globalvar.get_value("orders") or []))

    def cmd_riders(self, args):
        """Print the event log of every rider.

        Args:
            args: Unused.
        """
        print(self.display.format_rider_logs(self.system.riders))

    def cmd_map(self, args):
        """Print the ASCII map with riders and active orders.

        Args:
            args: Unused.
        """
        print(self.display.render_map(self.system.riders, self.orders.active_orders()))

    def cmd_tick(self, args):
        """Advance simulated time by ``n`` extra ticks.

        Args:
            args: Optional single integer token for the number of ticks.
        """
        steps = 1
        if args:
            try:
                steps = int(args[0])
            except ValueError:
                raise InputError(f"'{args[0]}' is not an integer") from None
            if not 1 <= steps <= 1000:
                raise InputError("tick count must be between 1 and 1000")
        self.advance(steps)
        print(f"Advanced {steps} tick(s); current tick is {self.system.tick}.")

    def cmd_save(self, args):
        """Save the system state to a JSON file.

        Args:
            args: Optional file path.
        """
        path = args[0] if args else None
        try:
            written = self.system.save_state(path)
        except OSError as exc:
            print(self.display.format_error(f"cannot save state: {exc}"))
            return
        print(f"State saved to {written}.")

    def cmd_history(self, args):
        """Print recent command history.

        Args:
            args: Unused.
        """
        print(self.inp.history_lines())

    def cmd_help(self, args):
        """Print the command help text.

        Args:
            args: Unused.
        """
        print(self.inp.help_text())

    def cmd_quit(self, args):
        """Stop the main loop.

        Args:
            args: Unused.
        """
        self.system.stop()
        print("Goodbye.")


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Optional argument list; defaults to ``sys.argv``.

    Returns:
        Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None, help="path to a JSON configuration file")
    parser.add_argument("--debug", action="store_true", help="log debug output to stderr")
    return parser.parse_args(argv)


def main(argv=None):
    """Program entry point.

    Args:
        argv: Optional argument list.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    cfg = config.load_config(args.config)
    setup_logging(cfg["log_file"], args.debug)
    try:
        app = DispatchApp(args.config)
        app.run()
    except Exception:
        logger.exception("Fatal error in dispatch simulator")
        print("Fatal error; see the log file for details.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
