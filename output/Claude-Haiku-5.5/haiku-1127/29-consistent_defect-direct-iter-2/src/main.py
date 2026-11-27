"""Command-line entry point for the Food Delivery Order Dispatch simulator.

Usage:
    python src/main.py [config.json]
"""

import logging
import math
import os
import sys
from typing import List, Optional

import globalvar
from display import DisplayManager
from input_manager import HELP_TEXT, InputError, InputManager
from path_planner import PathPlanner
from system import SystemManager

DEFAULT_STATE_FILE = "dispatch_state.json"
logger = logging.getLogger("dispatch")


class Application:
    """Interactive command loop tying all modules together."""

    def __init__(self) -> None:
        """Create the system, display and input managers."""
        self.system = SystemManager()
        self.display = DisplayManager()
        self.inp = InputManager()
        self.inp.setup_readline()

    # ----- main loop --------------------------------------------------
    def run(self) -> None:
        """Run the interactive loop until quit/exit or end of input."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.running:
            try:
                line = input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line.strip():
                continue
            self.inp.record_history(line)
            cmd, args = self.inp.parse_command(line)
            try:
                self.handle(cmd, args)
            except InputError as exc:
                print(f"Input error: {exc}")
            except Exception:  # error recovery: keep the session alive
                logger.exception("Unexpected error handling '%s'", cmd)
                print("An unexpected error occurred; system state preserved.")

    def handle(self, cmd: str, args: List[str]) -> None:
        """Dispatch a parsed command to its handler.

        Args:
            cmd: Canonical command name.
            args: Command arguments.
        """
        handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "save": self.cmd_save,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
            "": lambda _args: None,
        }
        handler = handlers.get(cmd)
        if handler is None:
            raise InputError(f"unknown command '{cmd}'. Type 'help'.")
        handler(args)

    # ----- commands ---------------------------------------------------
    def cmd_start(self, args: List[str]) -> None:
        """Create an order from four coordinates and assign a rider.

        Args:
            args: Optional four coordinates; prompts if omitted.
        """
        if not args:
            print("Enter: restaurant_x restaurant_y customer_x customer_y")
            tokens = input("start> ").split()
        else:
            tokens = args
        rx, ry, cx, cy = self.inp.validate_coordinates(tokens)

        result = self.system.submit_order((rx, ry), (cx, cy))
        order = result["order"]
        rider = result["rider"]

        print(f"Order #{order.id} created.")
        print(f"  Restaurant: input ({rx}, {ry}) -> grid {order.res_pos}")
        print(f"  Customer:   input ({cx}, {cy}) -> grid {order.cus_pos}")
        print(f"  New rider added: {'Yes' if result['new_rider'] else 'No'}")
        if rider is None:
            print("  No rider available (insufficient funds); order is pending.")
            return

        route = PathPlanner.plan_route(
            [rider.position, order.res_pos, order.cus_pos])
        length = PathPlanner.route_length(route)
        eta = math.ceil(length / rider.speed) if rider.speed else 0
        print(f"  Assigned rider: #{rider.rider_id} (state: {rider.state_name})")
        print(f"  Speed: {rider.speed} units/tick")
        print(f"  Estimated time: {eta} tick(s) for {length} units "
              f"(excludes previously queued orders)")
        print(self.display.render_map(
            riders=[rider], orders=[order], route=route))

    def cmd_status(self, _args: List[str]) -> None:
        """Print system funds, riders and their order lists."""
        print(self.display.render_status(
            funds=self.system.funds,
            riders=self.system.riders,
            tick=self.system.tick_count,
            pending=self.system.pending_count(),
        ))

    def cmd_orders(self, _args: List[str]) -> None:
        """Print details of all orders."""
        print(self.display.render_orders(self.system.order_manager.all_orders()))

    def cmd_riders(self, _args: List[str]) -> None:
        """Print the status-change log of every rider."""
        print(self.display.render_rider_logs(self.system.riders))

    def cmd_map(self, _args: List[str]) -> None:
        """Print the ASCII map of riders and orders."""
        print(self.display.render_map(
            riders=self.system.riders,
            orders=self.system.order_manager.all_orders()))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation by one or more ticks.

        Args:
            args: Optional number of ticks.
        """
        steps = self.inp.parse_tick_count(args)
        events = 0
        for _ in range(steps):
            events += self.system.tick()
        print(f"Advanced {steps} tick(s). Current tick: "
              f"{self.system.tick_count}. Rider events: {events}.")

    def cmd_save(self, args: List[str]) -> None:
        """Save the current state to a JSON file.

        Args:
            args: Optional output path.
        """
        path = args[0] if args else DEFAULT_STATE_FILE
        self.system.save_state(path)
        print(f"State saved to {path}.")

    def cmd_help(self, _args: List[str]) -> None:
        """Print the command help text."""
        print(HELP_TEXT)

    def cmd_quit(self, _args: List[str]) -> None:
        """Stop the main loop."""
        self.system.stop()
        print("Goodbye.")


def configure_logging() -> None:
    """Configure logging level from the DISPATCH_LOG environment variable."""
    level_name = os.environ.get("DISPATCH_LOG", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    configure_logging()
    args = sys.argv[1:] if argv is None else argv
    app = Application()
    if args:
        try:
            app.system.load_config(args[0])
        except (OSError, ValueError) as exc:
            print(f"Could not load configuration: {exc}. Using defaults.")
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
