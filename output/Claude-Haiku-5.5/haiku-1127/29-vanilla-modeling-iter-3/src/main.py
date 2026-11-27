"""Command-line entry point for the food delivery dispatch simulator.

Run with ``python src/main.py`` or ``python -m src.main`` from the project root.
Each iteration of the main loop reads one command, executes it and then
advances the simulation by one tick.
"""

import argparse
import logging
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_LOG_FILE, LOGGER, load_config, save_state  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputError, InputManager  # noqa: E402
from path_planner import PathPlanner  # noqa: E402
from order_model import STATUS_COMPLETED  # noqa: E402
from system import SystemManager, init_system  # noqa: E402

HELP_TEXT = """Commands:
  start [rx ry cx cy]  (s, n)  Create an order; prompts if no coordinates given
  status               (st)    Funds, riders, their locations, states and orders
  orders               (o)     Details of all orders
  riders               (r)     Log of every rider status change
  map                  (m)     ASCII map with riders, orders and routes
  tick [n]             (t)     Advance n extra ticks without other output
  history              (hist)  Command history (!! repeats last, !n repeats nth)
  help                 (h, ?)  Show this help
  quit                 (q, exit) Save state and exit
Coordinates are integers in 0-800. Each command is followed by one tick."""


class App:
    """Interactive command loop bound to a system, display and input manager.

    Attributes:
        system: The system manager.
        display: Output formatter.
        inp: Input manager.
        state_path: File where the state snapshot is written on exit.
        planner: Route planner used for the assignment preview.
    """

    def __init__(
        self,
        system: SystemManager,
        display: DisplayManager,
        inp: InputManager,
        state_path: Optional[str],
    ) -> None:
        """Bind the components together."""
        self.system = system
        self.display = display
        self.inp = inp
        self.state_path = state_path
        self.planner = PathPlanner()
        self._handlers = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "tick": self._cmd_tick,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
        }

    @staticmethod
    def _print_error(exc: Exception) -> None:
        """Print a user-friendly error message."""
        print(f"Error: {exc}")

    def run(self) -> None:
        """Run the main loop until quit or end of input."""
        print("Food Delivery Dispatch Simulator")
        print(HELP_TEXT)
        while self.system.is_running:
            try:
                line = self.inp.read_line("dispatch> ")
            except KeyboardInterrupt:
                print()
                break
            if line is None:
                print()
                break
            try:
                self.execute(line)
            except InputError as exc:
                self._print_error(exc)
            except Exception as exc:  # Error recovery: keep the simulation alive.
                LOGGER.exception("Unexpected error while executing '%s'", line)
                print(f"Unexpected error: {exc}. Attempting state recovery.")
                self.system.check_consistency()
            if self.system.is_running:
                self.system.tick()
        self.shutdown()

    def execute(self, line: str) -> None:
        """Expand, record and dispatch one command line.

        Args:
            line: Raw user input.

        Raises:
            InputError: On invalid history references or unknown commands.
        """
        expanded = self.inp.expand_history(line)
        if not expanded:
            return
        name, args = self.inp.parse_command(expanded)
        self.inp.add_history(expanded)
        handler = self._handlers.get(name)
        if handler is None:
            raise InputError(f"command '{name}' is not implemented")
        handler(args)

    def _cmd_start(self, args: List[str]) -> None:
        """Create an order, dispatch it and show the route map."""
        try:
            coords = (
                self.inp.parse_coordinates(args) if args else self.inp.prompt_coordinates()
            )
        except InputError as exc:
            self._print_error(exc)
            return
        rx, ry, cx, cy = coords
        order, rider, added = self.system.submit_order((rx, ry), (cx, cy))
        print(f"Order #{order.id} created.")
        print(f"  Restaurant grid cell centre: {order.res_pos}")
        print(f"  Customer grid cell centre:   {order.cus_pos}")
        print(f"New rider added: {'yes' if added else 'no'}")
        if rider is None:
            print(
                f"No rider available (funds: {self.system.funds}). "
                "The order is pending and will be dispatched when a rider is available."
            )
            return
        print(
            f"Assigned to rider #{rider.rider_id} "
            f"(speed {rider.speed} units/tick, status {rider.state_name})."
        )
        route = [rider.position] + self.planner.plan_multi(
            rider.position, [order.res_pos, order.cus_pos]
        )
        print(self.display.render_map(self.system.riders, [order], route))
        print(self.display.format_route_summary(order, rider, route))

    def _cmd_status(self, args: List[str]) -> None:
        """Print the system snapshot."""
        print(self.display.format_status(self.system))

    def _cmd_orders(self, args: List[str]) -> None:
        """Print details of all orders."""
        print(self.display.format_orders(self.system.order_manager.history))

    def _cmd_riders(self, args: List[str]) -> None:
        """Print every recorded rider status change."""
        print(self.display.format_rider_logs(self.system.riders))

    def _cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map with riders and active orders."""
        active = [
            o for o in self.system.order_manager.history if o.status != STATUS_COMPLETED
        ]
        print(self.display.render_map(self.system.riders, active))

    def _cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation by an additional number of ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                self._print_error(InputError("tick count must be an integer"))
                return
            if not 1 <= count <= 1000:
                self._print_error(InputError("tick count must be between 1 and 1000"))
                return
        for _ in range(count):
            self.system.tick()
        print(f"Advanced {count} tick(s). Current tick: {self.system.current_tick}")

    def _cmd_history(self, args: List[str]) -> None:
        """Print the command history with 1-based indices."""
        history = self.inp.command_history
        if not history:
            print("No command history.")
            return
        for index, entry in enumerate(history, start=1):
            print(f"{index:>4}  {entry}")

    def _cmd_help(self, args: List[str]) -> None:
        """Print the command reference."""
        print(HELP_TEXT)

    def _cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.is_running = False
        print("Exiting dispatch simulator.")

    def shutdown(self) -> None:
        """Persist the system state to disk."""
        path = self.state_path or self.system.settings.get("state_file")
        if not path:
            return
        try:
            save_state(path, self.system.to_dict())
            print(f"State saved to {path}.")
        except OSError as exc:
            LOGGER.error("Failed to save state to %s: %s", path, exc)
            print(f"Warning: could not save state: {exc}")


def setup_logging(debug: bool, log_file: str) -> None:
    """Configure file logging for debugging and diagnostics.

    Logs go to a file so that the interactive output stays clean.

    Args:
        debug: If True, log at DEBUG level; otherwise INFO.
        log_file: Destination log file path.
    """
    level = logging.DEBUG if debug else logging.INFO
    LOGGER.setLevel(level)
    try:
        handler = logging.FileHandler(log_file, encoding="utf-8")
    except OSError:
        handler = logging.NullHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    LOGGER.addHandler(handler)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="path to a JSON configuration file")
    parser.add_argument("--state", help="path of the JSON state file written on exit")
    parser.add_argument("--log-file", default=DEFAULT_LOG_FILE, help="log file path")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Optional argument list.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    setup_logging(args.debug, args.log_file)
    settings = load_config(args.config)
    if args.state:
        settings["state_file"] = args.state
    system = init_system(settings)
    app = App(system, DisplayManager(), InputManager(), settings["state_file"])
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
