"""Command-line entry point for the food delivery dispatch simulator.

Run with::

    python src/main.py [--config settings.json] [--log-level INFO]

Each iteration of the main loop is one simulated tick: the command typed (or
an empty line) is executed and then the simulation advances by one tick.
"""

import argparse
import logging
import math
import sys

import config
from config import SETTINGS
from display import DisplayManager
from input_manager import InputManager
from path_planner import PathPlanner
from persistence import save_state
from system import init_system

logger = logging.getLogger("dispatch")

BANNER = """\
=====================================================
  Food Delivery Order Dispatch System (simulator)
  Type 'help' for commands. Each command = one tick.
====================================================="""

HELP_TEXT = """\
Commands:
  start [rx ry cx cy]  Create an order (prompts if omitted), assign the
                       closest rider, show the route map.
  status               Funds, riders, their state and order lists.
  orders               Details of all orders.
  riders               Status-change log of every rider.
  map                  ASCII map of riders and active orders.
  tick [n]             Advance the simulation by n ticks (default 1).
  save [file]          Save the state to a JSON file.
  history              Show command history (reuse with !! or !N).
  help                 Show this help.
  quit | exit          Leave the program.
Shortcuts: s=start st=status o=orders r=riders m=map t=tick h=help q=quit
Coordinates are integers in 0-800. Locations snap to grid cell centres."""


class CommandLineInterface:
    """Runs the interactive command loop.

    Args:
        system: The SystemManager returned by ``init_system``.
    """

    def __init__(self, system):
        self.system = system
        self.inputs = InputManager()
        self.display = DisplayManager()
        self._commands = {
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
            "exit": self.cmd_quit,
        }

    def run(self):
        """Run the main loop until the system is shut down."""
        print(BANNER)
        while self.system.running:
            line = self.inputs.read_line("dispatch> ")
            if line is None:
                print()
                self.system.shutdown()
                break
            line = line.strip()
            try:
                expanded = self.inputs.expand_history(line)
            except ValueError as exc:
                print(f"Error: {exc}")
                expanded = None
            if expanded is not None:
                if expanded:
                    self.inputs.add_history(expanded)
                self._execute(expanded)
            if self.system.running:
                self._advance_clock()
        print("Goodbye.")

    def _execute(self, line):
        """Parse and run one command, reporting errors without crashing.

        Args:
            line: Command text.
        """
        name, args = InputManager.parse_command(line)
        if not name:
            return
        handler = self._commands.get(name)
        if handler is None:
            print(f"Unknown command '{name}'. Type 'help' for a list of commands.")
            return
        try:
            handler(args)
        except (ValueError, LookupError, RuntimeError) as exc:
            print(f"Error: {exc}")
        except EOFError:
            print()
            self.system.shutdown()
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unexpected error while running '%s'", name)
            print(f"Internal error: {exc}. The system state was preserved.")

    def _advance_clock(self):
        """Advance one tick and repair any detected inconsistency."""
        try:
            self.system.tick()
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Tick failed")
            print(f"Warning: simulation tick failed: {exc}")
        for issue in self.system.check_consistency():
            logger.warning("Consistency repair: %s", issue)

    # ------------------------------------------------------------------ #
    # Command handlers
    # ------------------------------------------------------------------ #
    def cmd_start(self, args):
        """Create an order, assign a rider and display the route map.

        Args:
            args: Four coordinate tokens, or an empty list to prompt.
        """
        if args:
            coords = InputManager.parse_coordinates(args)
        else:
            coords = self.inputs.prompt_coordinates()

        order, rider, recruited = self.system.submit_order(coords)
        res_x, res_y = order.res_pos
        cus_x, cus_y = order.cus_pos
        print(f"Order #{order.id} created at tick {order.start_time}")
        print(f"  Restaurant grid cell ({res_x // 100}, {res_y // 100}), "
              f"centre {order.res_pos}")
        print(f"  Customer grid cell ({cus_x // 100}, {cus_y // 100}), "
              f"centre {order.cus_pos}")
        if recruited:
            print(f"  New rider added: Rider #{rider.rider_id} "
                  f"(cost {SETTINGS['recruit_cost']}, funds now "
                  f"{self.system.funds})")
        if rider is None:
            print("  No rider available (insufficient funds). The order stays "
                  "pending and is retried every tick.")
            return

        print(f"  Assigned to Rider #{rider.rider_id} "
              f"(distance to restaurant {rider.distance_to(order.res_pos):.1f})")
        stops = []
        for queued in rider.orders:
            stops.extend([queued.res_pos, queued.cus_pos])
        route = PathPlanner.plan_multi_stop(rider.position(), stops)
        length = PathPlanner.route_length(rider.position(), route)
        ticks = math.ceil(length / rider.speed) if rider.speed else 0
        print(f"  Speed: {rider.speed} units/tick, route length {length} units, "
              f"estimated {ticks} tick(s)")
        print("Route map:")
        print(self.display.render_map(
            riders=[rider],
            orders=[order],
            route=[rider.position()] + route,
        ))

    def cmd_status(self, _args):
        """Print the system status snapshot.

        Args:
            _args: Unused.
        """
        print(self.display.format_status(self.system))

    def cmd_orders(self, _args):
        """Print the table of all orders.

        Args:
            _args: Unused.
        """
        print(self.display.format_orders(self.system.order_manager.all_orders()))

    def cmd_riders(self, _args):
        """Print every rider's status-change log.

        Args:
            _args: Unused.
        """
        print(self.display.format_rider_logs(self.system.riders))

    def cmd_map(self, _args):
        """Print the ASCII map with riders and active orders.

        Args:
            _args: Unused.
        """
        print(self.display.render_map(
            riders=self.system.riders,
            orders=self.system.order_manager.active_orders(),
        ))

    def cmd_tick(self, args):
        """Advance the simulation by one or more ticks.

        Args:
            args: Optional tick count.

        Raises:
            ValueError: If the count is not an integer in 1-10000.
        """
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"Tick count must be an integer, got '{args[0]}'.")
            if not 1 <= count <= 10000:
                raise ValueError("Tick count must be between 1 and 10000.")
        for _ in range(count):
            self.system.tick()
        print(f"Advanced {count} tick(s); now at tick {self.system.tick_count}.")

    def cmd_save(self, args):
        """Save the state to a JSON file.

        Args:
            args: Optional file path.

        Raises:
            RuntimeError: If the file cannot be written.
        """
        try:
            path = save_state(args[0] if args else None)
        except OSError as exc:
            raise RuntimeError(f"Could not save state: {exc}") from None
        print(f"State saved to {path}.")

    def cmd_history(self, _args):
        """Print the command history with 1-based indices.

        Args:
            _args: Unused.
        """
        history = self.inputs.history
        if not history:
            print("No command history.")
            return
        for index, command in enumerate(history, start=1):
            print(f"  {index:>3}  {command}")

    def cmd_help(self, _args):
        """Print the help text.

        Args:
            _args: Unused.
        """
        print(HELP_TEXT)

    def cmd_quit(self, _args):
        """Stop the program.

        Args:
            _args: Unused.
        """
        self.system.shutdown()
        print("Shutting down...")


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Argument list, or None for ``sys.argv``.

    Returns:
        argparse.Namespace: Parsed options.
    """
    parser = argparse.ArgumentParser(
        description="Food delivery order dispatch simulator.")
    parser.add_argument("--config", help="JSON file overriding system parameters")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity (default WARNING)")
    parser.add_argument("--log-file", default=None,
                        help="Write logs to this file instead of stderr")
    return parser.parse_args(argv)


def main(argv=None):
    """Program entry point.

    Args:
        argv: Optional argument list.

    Returns:
        int: Process exit code.
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        filename=args.log_file,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.config:
        try:
            config.load_config_file(args.config)
            logger.info("Loaded configuration from %s", args.config)
        except (OSError, ValueError) as exc:
            print(f"Could not load configuration ({exc}). Using defaults.")
            logger.warning("Configuration load failed: %s", exc)

    system = init_system()
    CommandLineInterface(system).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
