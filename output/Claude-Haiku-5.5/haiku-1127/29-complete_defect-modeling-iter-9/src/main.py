"""Command-line entry point for the Food Delivery Order Dispatch simulator.

Run with:  python src/main.py [--config config.json] [--log-level INFO]
"""

import argparse
import logging
import sys

from config import LOGGER, load_config
from display import DisplayManager
from input_manager import InputManager
from order_model import grid_cell_of
from system import SystemManager, init_system


class DispatchApp:
    """Main interactive loop tying together system, display and input.

    Attributes:
        system: The SystemManager instance.
        display: The DisplayManager instance.
        inp: The InputManager instance.
        input_func: Callable used to read user input.
        output: Callable used to print output.
    """

    def __init__(self, system: SystemManager, display: DisplayManager,
                 inp: InputManager, input_func=input, output=print):
        """Create the application.

        Args:
            system: Initialised SystemManager.
            display: DisplayManager for rendering.
            inp: InputManager for parsing.
            input_func: Input reader (injectable for testing).
            output: Output writer (injectable for testing).
        """
        self.system = system
        self.display = display
        self.inp = inp
        self.input_func = input_func
        self.output = output

    def run(self) -> None:
        """Run the main loop: one iteration per simulated tick."""
        self.output("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.running_state:
            try:
                line = self.input_func("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self.output("")
                break
            self.run_once(line)
        self._save_on_exit()

    def run_once(self, line: str) -> None:
        """Process one input line and advance the simulation by one tick.

        Args:
            line: Raw input line.
        """
        try:
            resolved = self.inp.resolve_line(line)
            command = self.inp.parse(resolved)
            self.inp.record(resolved)
            self.dispatch(command)
        except ValueError as exc:
            self.output(f"Error: {exc}")
        except Exception:  # error recovery: never crash the main loop
            LOGGER.exception("Unexpected error while handling command")
            self.output("Internal error occurred; system state has been checked and repaired.")
            for issue in self.system.check_consistency():
                LOGGER.warning("Repaired: %s", issue)

        if self.system.running_state:
            try:
                self.system.tick()
            except Exception:
                LOGGER.exception("Unexpected error during tick")
                self.system.check_consistency()

    def dispatch(self, command) -> None:
        """Route a parsed command to its handler.

        Args:
            command: Command object produced by InputManager.parse.

        Raises:
            ValueError: For invalid arguments.
        """
        handlers = {
            "": self.cmd_idle,
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "wait": self.cmd_wait,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }
        handlers[command.name](command.arguments)

    def cmd_idle(self, args) -> None:
        """Handle an empty line: only the per-iteration tick occurs."""
        return None

    def cmd_start(self, args) -> None:
        """Create an order, recruit if needed, assign and show the route.

        Args:
            args: Either empty (interactive prompt) or four coordinate tokens.

        Raises:
            ValueError: On invalid coordinates or when no rider is available.
        """
        if not args:
            coords = self.inp.prompt_coordinates(self.input_func, self.output)
        elif len(args) == 4:
            coords = self.inp.validate_coordinates(args)
        else:
            raise ValueError("start expects 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y")
        restaurant_pos = coords[0:2]
        customer_pos = coords[2:4]

        manager = self.system.order_manager
        order = manager.create_order(restaurant_pos, customer_pos, self.system.current_tick)
        new_rider = self.system.check_recruitment()
        rider = manager.assign_order(order)
        if rider is None:
            manager.cancel_order(order)
            raise ValueError("no rider is available and recruitment is not possible "
                             "(check funds and rider limit)")

        route = self.system.path_planner.plan_route(
            rider.position, [order.restaurant, order.customer])

        self.output(f"Order #{order.id} accepted at tick {order.start_time}.")
        self.output(f"Restaurant input {tuple(order.res_pos)} -> grid cell "
                    f"{grid_cell_of(order.res_pos)} center {order.restaurant}")
        self.output(f"Customer input {tuple(order.cus_pos)} -> grid cell "
                    f"{grid_cell_of(order.cus_pos)} center {order.customer}")
        if new_rider:
            self.output(f"New rider recruited: #{self.system.riders[-1].rider_id}")
        else:
            self.output("No new rider recruited.")
        self.output(self.display.format_route_summary(route, rider))
        self.output("Route map:")
        self.output(self.display.render_map(
            riders=[rider], orders=[order],
            route=(rider.position, route.waypoints)))
        self.output(self.display.legend())

    def cmd_status(self, args) -> None:
        """Show the system fund balance and the status of all riders."""
        self.output(self.display.format_status(
            self.system.funds, self.system.riders,
            self.system.order_manager.active_orders()))

    def cmd_orders(self, args) -> None:
        """Show the details of all orders."""
        self.output(self.display.format_orders(self.system.order_manager.orders))

    def cmd_riders(self, args) -> None:
        """Show the status-change log of every rider."""
        self.output(self.display.format_rider_log(self.system.riders))

    def cmd_map(self, args) -> None:
        """Show the ASCII map with riders and active orders."""
        self.output(self.display.render_map(
            riders=self.system.riders,
            orders=self.system.order_manager.active_orders()))
        self.output(self.display.legend())

    def cmd_wait(self, args) -> None:
        """Advance the simulation by extra ticks.

        Args:
            args: Optional single integer count (default 1, max 1000).

        Raises:
            ValueError: If the count is invalid.
        """
        count = 1
        if args:
            if len(args) != 1:
                raise ValueError("wait accepts at most one argument")
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"wait count must be an integer, got '{args[0]}'") from None
            if not 1 <= count <= 1000:
                raise ValueError("wait count must be between 1 and 1000")
        for _ in range(count):
            self.system.tick()
        self.output(f"Advanced {count} tick(s); current tick is {self.system.current_tick}.")

    def cmd_history(self, args) -> None:
        """Show the numbered command history."""
        if not self.inp.command_history:
            self.output("History is empty.")
            return
        for index, entry in enumerate(self.inp.command_history, start=1):
            self.output(f"  {index:>3}  {entry}")

    def cmd_help(self, args) -> None:
        """Show command help."""
        self.output(self.inp.help_text())

    def cmd_quit(self, args) -> None:
        """Stop the main loop."""
        self.system.running_state = False
        self.output("Goodbye.")

    def _save_on_exit(self) -> None:
        """Persist the system state to the configured file if enabled."""
        if self.system.config.get("save_on_exit", False):
            path = self.system.config.get("state_file", "dispatch_state.json")
            if self.system.save_state(path):
                self.output(f"State saved to {path}.")
            else:
                self.output(f"Warning: could not save state to {path}.")


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None,
                        help="path to a JSON configuration file")
    parser.add_argument("--log-file", default=None,
                        help="optional path for debug log output")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="logging verbosity")
    return parser.parse_args(argv)


def setup_logging(level: str, log_file: str = None) -> None:
    """Configure the root dispatch logger.

    Args:
        level: Logging level name.
        log_file: Optional file to receive log output.
    """
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main(argv=None) -> int:
    """Program entry point.

    Args:
        argv: Optional argument list.

    Returns:
        int: Process exit status.
    """
    args = parse_args(argv)
    setup_logging(args.log_level, args.log_file)
    config = load_config(args.config)
    system = init_system(config)
    app = DispatchApp(system, DisplayManager(), InputManager())
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
