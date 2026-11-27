"""Command-line entry point for the food delivery dispatch simulator.

Run with::

    python src/main.py [--config dispatch_config.json] [--log-level INFO]
"""

import argparse
import logging
import sys

import config
import system
from display import DisplayManager
from input_manager import HELP_TEXT, InputManager
from order import NoRiderAvailableError, OrderManager
from order_model import STATUS_COMPLETED

logger = logging.getLogger("dispatch.main")


class DispatchApp:
    """Interactive command loop wiring all managers together.

    Args:
        config_path: Optional JSON configuration file.
        reader: Input callable (defaults to ``input``).
        writer: Output callable (defaults to ``print``).
    """

    def __init__(self, config_path=None, reader=input, writer=print):
        self.manager = system.init_system(config_path)
        self.orders = OrderManager(self.manager)
        self.display = DisplayManager()
        self.inputs = InputManager(reader, writer)
        self.out = writer
        self._handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    def run(self):
        """Run the main loop until the user quits.

        Returns:
            int: Process exit code (0 on normal exit).
        """
        self.out("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.manager.running:
            try:
                command, args = self.inputs.read_command()
            except (EOFError, KeyboardInterrupt):
                self.out("")
                self.out("Exiting.")
                self.manager.stop()
                break
            if not command:
                continue
            self.dispatch(command, args)
            self._self_check()
        self._save_on_exit()
        return 0

    def dispatch(self, command, args):
        """Execute one command, reporting errors without terminating.

        Args:
            command: Canonical command name.
            args: Command arguments.
        """
        handler = self._handlers.get(command)
        if handler is None:
            self.out(f"Unknown command '{command}'. Type 'help' for the list of commands.")
            return
        try:
            handler(args)
        except (ValueError, NoRiderAvailableError) as exc:
            self.out(f"Error: {exc}")
        except Exception:  # noqa: BLE001 - recover and keep running
            logger.exception("Unexpected failure while running '%s'", command)
            self.out("Unexpected internal error; the system state has been kept consistent.")

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def cmd_start(self, args):
        """Place an order, assign a rider and simulate until delivery."""
        if args:
            values = self.inputs.parse_coordinates(args)
        else:
            values = self.inputs.prompt_coordinates()
            if values is None:
                self.out("Order input cancelled.")
                return

        order = self.orders.create_order(values)
        rider, new_rider = self.orders.assign_order(order)
        self.out(self.display.render_order_placed(order, rider, new_rider))

        trail = [rider.position]
        ticks = 0
        while order.status != STATUS_COMPLETED:
            if ticks >= config.MAX_SIMULATION_TICKS:
                self.out(
                    f"Warning: order #{order.id} not completed after "
                    f"{config.MAX_SIMULATION_TICKS} ticks; stopping the preview."
                )
                break
            self.manager.advance(1)
            ticks += 1
            trail.append(rider.position)

        self.out(self.display.render_route(order, rider, trail))

    def cmd_status(self, args):
        """Show funds, riders and their order lists."""
        self.out(self.display.render_status(self.manager.funds, self.manager.riders, self.manager.tick))
        active = self.orders.active_orders()
        self.out(f"Active orders: {len(active)}")

    def cmd_orders(self, args):
        """Show the details of every order."""
        self.out(self.display.render_orders(self.orders.all_orders()))

    def cmd_riders(self, args):
        """Show the status-change log of every rider."""
        self.out(self.display.render_rider_logs(self.manager.riders))

    def cmd_map(self, args):
        """Show the ASCII map of riders and active orders."""
        self.out(self.display.render_map(riders=self.manager.riders, orders=self.orders.active_orders()))

    def cmd_tick(self, args):
        """Advance the simulation clock by a number of ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"'{args[0]}' is not an integer tick count") from None
        if not 1 <= count <= config.MAX_MANUAL_TICKS:
            raise ValueError(f"tick count must be between 1 and {config.MAX_MANUAL_TICKS}")
        self.manager.advance(count)
        self.out(f"Advanced {count} tick(s). Current tick: {self.manager.tick}")

    def cmd_history(self, args):
        """Show previously entered commands."""
        history = self.inputs.history()
        if not history:
            self.out("No command history yet.")
            return
        for index, line in enumerate(history, start=1):
            self.out(f"{index:>4}  {line}")

    def cmd_help(self, args):
        """Show the command reference."""
        self.out(HELP_TEXT)

    def cmd_quit(self, args):
        """Stop the main loop."""
        self.manager.stop()
        self.out("Goodbye.")

    # ------------------------------------------------------------------
    # Support
    # ------------------------------------------------------------------
    def _self_check(self):
        """Run consistency checks after each command and report repairs."""
        issues = self.manager.check_consistency()
        if issues:
            self.out(f"Note: repaired {len(issues)} consistency issue(s); see the log for details.")

    def _save_on_exit(self):
        """Persist the system state; failures are logged, not raised."""
        try:
            self.manager.save_state(config.STATE_FILE)
        except OSError as exc:
            logger.error("Could not save state to %s: %s", config.STATE_FILE, exc)


def setup_logging(level_name):
    """Configure logging to the log file, falling back to warnings on stderr.

    Args:
        level_name: Logging level name such as ``"INFO"``.
    """
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    try:
        logging.basicConfig(filename=config.LOG_FILE, level=level, format=fmt, encoding="utf-8")
    except OSError:
        logging.basicConfig(level=logging.WARNING, format=fmt)


def main(argv=None):
    """Parse arguments and run the dispatch simulator.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        int: Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument(
        "--config",
        default=config.CONFIG_FILE,
        help="JSON configuration file with system parameters",
    )
    parser.add_argument("--log-level", default="INFO", help="logging level (default: INFO)")
    args = parser.parse_args(argv)

    setup_logging(args.log_level)
    app = DispatchApp(config_path=args.config)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
