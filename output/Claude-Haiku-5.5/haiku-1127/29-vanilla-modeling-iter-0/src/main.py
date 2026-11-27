"""Command-line entry point for the food delivery dispatch simulator.

Run with:  python src/main.py [--config dispatch_config.json]
"""

import argparse
import logging
import os
import sys
from typing import Callable, Dict, List, Optional

import globalvar
from display import DisplayManager
from input_manager import CommandError, InputManager
from order import OrderManager
from persistence import load_config, save_state
from system import init_system, SystemManager

LOGGER = logging.getLogger("dispatch.main")

MAX_SIMULATION_TICKS = 2000
DEFAULT_CONFIG_PATH = "dispatch_config.json"
DEFAULT_SAVE_PATH = "dispatch_state.json"


class DispatchApp:
    """Interactive command loop tying all modules together."""

    def __init__(self, config_path: Optional[str] = None,
                 input_func: Callable[[str], str] = input,
                 output: Callable[..., None] = print) -> None:
        """Initialise the system and the interactive components.

        Args:
            config_path: Optional JSON configuration file.
            input_func: Function used to read user input.
            output: Function used to print output.
        """
        self.system: SystemManager = init_system(load_config(config_path))
        self.order_manager = OrderManager()
        self.display = DisplayManager()
        self.inputs = InputManager()
        self._input = input_func
        self._output = output
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
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

    def run(self) -> None:
        """Run the main loop until the system stops or input ends."""
        self._output("Food Delivery Dispatch Simulator. "
                     "Type 'help' for commands.")
        while self.system.is_running():
            try:
                line = self._input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self._output("")
                break
            if not line or not line.strip():
                continue
            try:
                self.execute(line)
            except (EOFError, KeyboardInterrupt):
                self._output("")
                break
        self._output("Goodbye.")

    def execute(self, line: str) -> None:
        """Parse and run one command line with error recovery.

        Args:
            line: Raw user input.
        """
        try:
            command, args = self.inputs.resolve_line(line)
            self._handlers[command](args)
        except CommandError as exc:
            self._output(f"Error: {exc}")
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception as exc:  # error recovery path
            LOGGER.exception("Unexpected error while executing %r", line)
            self._output(f"Internal error: {exc}. Attempting state repair.")
            fixes = self.order_manager.repair_state()
            self._output(f"State check complete ({fixes} repair(s)).")

    def _tick_once(self) -> None:
        """Advance one tick, recruit if needed and assign pending orders."""
        self.system.tick()
        self.system.maybe_recruit()
        self.order_manager.assign_pending()

    def cmd_start(self, args: List[str]) -> None:
        """Place an order and simulate it until delivery."""
        if not args:
            args = self._input(
                "Enter restaurant_x restaurant_y customer_x customer_y: "
            ).split()
        coords = self.inputs.parse_coordinates(args)
        start_time = self.system.simulated_time
        order = self.order_manager.submit_order((coords[0], coords[1]),
                                                (coords[2], coords[3]))
        new_rider = self.system.maybe_recruit()
        assignments = self.order_manager.assign_pending()
        rider = next((r for o, r in assignments if o is order), None)

        if rider is None:
            self._output(f"Order #{order.id} queued: no rider available "
                         f"(funds={self.system.funds}).")
            return

        self._output(f"Order #{order.id} accepted.")
        self._output(f"  Restaurant (grid center): "
                     f"({order.restaurant_x}, {order.restaurant_y})")
        self._output(f"  Customer (grid center): "
                     f"({order.customer_x}, {order.customer_y})")
        if new_rider is not None:
            self._output(f"  New rider added: #{new_rider.rider_id} "
                         f"(funds now {self.system.funds})")
        else:
            self._output("  New rider added: no")
        self._output(f"  Assigned rider: #{rider.rider_id} "
                     f"speed={rider.speed} units/tick")

        ticks = 0
        while order.status != "completed" and ticks < MAX_SIMULATION_TICKS:
            self._tick_once()
            ticks += 1

        if order.status == "completed":
            self._output(f"  Delivered in {order.time_taken} tick(s); "
                         f"route length {order.distance:.0f} units.")
        else:
            self._output(f"  Not delivered after {ticks} ticks; "
                         f"use 'orders' to track progress.")

        route = [(x, y) for (t, x, y) in rider.path_history if t >= start_time]
        self._output(self.display.render_map(
            self.system.riders, self.order_manager.all_orders(), route))

    def cmd_status(self, args: List[str]) -> None:
        """Show funds, time and rider snapshot."""
        self._output(self.display.render_status(
            self.system.funds, self.system.simulated_time, self.system.riders))

    def cmd_orders(self, args: List[str]) -> None:
        """Show details of all orders."""
        self._output(self.display.render_orders(
            self.order_manager.all_orders()))

    def cmd_riders(self, args: List[str]) -> None:
        """Show the status change log of all riders."""
        self._output(self.display.render_rider_logs(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map with riders and orders."""
        self._output(self.display.render_map(
            self.system.riders, self.order_manager.all_orders()))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation by one or more ticks."""
        count = self.inputs.parse_count(args)
        for _ in range(count):
            self._tick_once()
        self._output(f"Simulated time is now {self.system.simulated_time}.")

    def cmd_save(self, args: List[str]) -> None:
        """Save the system state to a JSON file."""
        path = args[0] if args else DEFAULT_SAVE_PATH
        try:
            save_state(path)
        except OSError as exc:
            raise CommandError(f"Could not save to {path}: {exc}") from None
        self._output(f"State saved to {path}.")

    def cmd_history(self, args: List[str]) -> None:
        """List recently entered commands."""
        history = self.inputs.command_history
        if not history:
            self._output("No command history yet.")
            return
        for index, entry in enumerate(history, start=1):
            self._output(f"  {index:>3}  {entry}")

    def cmd_help(self, args: List[str]) -> None:
        """Show the command help."""
        self._output(self.inputs.help_text())

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.shutdown()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH,
                        help="JSON file with system parameter overrides")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity for debugging")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Optional argument list (defaults to sys.argv[1:]).

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config_path = args.config if os.path.exists(args.config) else None
    app = DispatchApp(config_path=config_path)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
