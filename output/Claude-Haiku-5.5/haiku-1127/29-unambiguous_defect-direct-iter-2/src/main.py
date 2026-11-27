"""Entry point for the food delivery dispatch simulator.

Run with ``python src/main.py``. Each iteration of the main loop is one
simulated tick: the user's command is processed and then the simulation
advances by one unit of time.
"""

import argparse
import logging
import math
import os
import sys
from typing import List, Optional

from display_manager import DisplayManager
from input_manager import InputManager
from order import OrderManager
from path_planner import PathPlanner
from system import CONFIG_FILE, DEFAULT_STATE_FILE, SystemManager, init_system, load_config

logger = logging.getLogger("dispatch")
LOG_FILE = "dispatch.log"
MAX_WAIT_TICKS = 1000


def setup_logging(debug: bool, log_file: str = LOG_FILE) -> None:
    """Configure logging to a file, falling back to stderr."""
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    try:
        logging.basicConfig(filename=log_file, level=level, format=fmt)
    except OSError:
        logging.basicConfig(level=level, format=fmt)


class DispatchApp:
    """Interactive command loop tying all modules together."""

    def __init__(self, system: SystemManager) -> None:
        self.system = system
        self.orders = OrderManager()
        self.display = DisplayManager()
        self.inputs = InputManager()

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        """Run the simulation loop until the user quits."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands. Each command advances the simulation by one tick.")
        while self.system.is_running:
            try:
                command, args = self.inputs.read_command()
                if command:
                    self.dispatch(command, args)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                break
            except ValueError as exc:
                print(f"Error: {exc}")
            except Exception:  # noqa: BLE001 - keep the simulator alive
                logger.exception("Unexpected error while processing command")
                print("Internal error occurred; the system state has been checked and kept running.")
                self.system.check_consistency()

            if self.system.is_running:
                self.system.tick()
        print("Goodbye.")

    def dispatch(self, command: str, args: List[str]) -> None:
        """Route a parsed command to its handler."""
        handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "wait": self.cmd_wait,
            "save": self.cmd_save,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }
        handlers[command](args)

    # ------------------------------------------------------------------ #
    # Command handlers
    # ------------------------------------------------------------------ #
    def cmd_start(self, args: List[str]) -> None:
        """Create an order, assign a rider and show the planned route."""
        coords = self.inputs.parse_order_args(args)
        order = self.orders.create_order(coords)
        rider, is_new = self.orders.assign_order(order, self.system)
        if rider is None:
            print(
                "No rider available: recruitment failed (insufficient funds or rider "
                "limit reached). Order cancelled."
            )
            return
        route = PathPlanner.full_route(rider.position, order.res_pos, order.cus_pos)
        length = PathPlanner.route_length(route)
        estimated = math.ceil(length / rider.speed) if length else 0
        print(self.display.order_report(order, rider, length, estimated, is_new))
        print(self.display.render_map(self.system.riders, orders=[order], route=route))

    def cmd_status(self, args: List[str]) -> None:
        """Show funds, riders and the current map."""
        print(
            self.display.status_report(
                self.system.funds, self.system.riders, self.system.tick_count
            )
        )
        print(
            self.display.render_map(
                self.system.riders, orders=self.orders.active_orders()
            )
        )

    def cmd_orders(self, args: List[str]) -> None:
        """Show all orders."""
        print(self.display.orders_report(self.orders.history()))

    def cmd_riders(self, args: List[str]) -> None:
        """Show the event log of all riders."""
        print(self.display.riders_report(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map with riders and active orders."""
        print(self.display.render_map(self.system.riders, orders=self.orders.active_orders()))

    def cmd_wait(self, args: List[str]) -> None:
        """Advance the simulation by extra ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError("wait expects a whole number of ticks") from None
        if not 1 <= count <= MAX_WAIT_TICKS:
            raise ValueError(f"wait count must be between 1 and {MAX_WAIT_TICKS}")
        for _ in range(count - 1):
            self.system.tick()
        print(f"Advanced {count} tick(s); simulated tick is now {self.system.tick_count + 1}"
              f" after this command.")

    def cmd_save(self, args: List[str]) -> None:
        """Save the system state to a JSON file."""
        path = args[0] if args else DEFAULT_STATE_FILE
        if self.system.save_state(path):
            print(f"State saved to {path}.")
        else:
            print(f"Could not write to {path}; see the log for details.")

    def cmd_history(self, args: List[str]) -> None:
        """Print the numbered command history."""
        history = self.inputs.history
        if not history:
            print("No commands yet.")
            return
        for index, entry in enumerate(history, start=1):
            print(f"  {index:>3}  {entry}")

    def cmd_help(self, args: List[str]) -> None:
        """Print help text."""
        print(self.inputs.help_text())

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the simulation loop."""
        self.system.stop()


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Optional command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=CONFIG_FILE, help="JSON configuration file")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    parser.add_argument("--log-file", default=LOG_FILE, help="log file path")
    args = parser.parse_args(argv)

    setup_logging(args.debug, args.log_file)
    system = init_system()
    if os.path.exists(args.config):
        load_config(args.config)
    app = DispatchApp(system)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
