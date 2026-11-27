"""Entry point for the food delivery dispatch simulator command-line tool.

Run with: ``python src/main.py``
"""

import logging
import sys
from typing import Callable, List, Optional

import config
import globalvar
from display_manager import DisplayManager
from input_manager import CommandError, InputManager
from path_planner import PathPlanner
from system import SystemManager

logger = logging.getLogger("dispatch")

BANNER = "Food Delivery Dispatch Simulator. Type 'help' for commands."


class DispatchApp:
    """Command dispatcher tying together the system, display and input modules."""

    def __init__(self, reader: Callable[[str], str] = input,
                 writer: Callable[[str], None] = print,
                 config_path: str = config.DEFAULT_CONFIG_PATH) -> None:
        """Build the application.

        Args:
            reader: Line reader (``input`` by default).
            writer: Output function (``print`` by default).
            config_path: Optional JSON configuration file.
        """
        params = config.load_config(config_path)
        self.system = SystemManager(params)
        self.display = DisplayManager()
        self.inp = InputManager(reader, writer)
        self.out = writer
        self._handlers = {
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

    def handle(self, name: str, args: List[str]) -> None:
        """Dispatch a parsed command to its handler."""
        self._handlers[name](args)

    def cmd_start(self, args: List[str]) -> None:
        """Create an order, assign it, and run it to completion."""
        coords = self.inp.parse_coordinates(args) if args else self.inp.prompt_order()
        order, rider, recruited = self.system.submit_order(*coords)
        for new_rider in recruited:
            self.out(f"New rider #{new_rider.rider_id} recruited "
                     f"(cost {self.system._cfg('recruit_cost')}, "
                     f"system funds now {self.system.get_funds()})")
        if rider is None:
            self.out(f"No rider available and funds ({self.system.get_funds()}) are too "
                     f"low to recruit. Order #{order.id} remains pending.")
            return

        start_pos = rider.position
        trip = PathPlanner.plan_trip(start_pos, order.res_pos, order.cus_pos)
        trip_distance = PathPlanner.route_length(trip)
        estimated = PathPlanner.estimate_ticks(trip_distance, rider.speed)
        try:
            actual = self.system.run_until_complete(order)
        except RuntimeError as exc:
            self.out(f"Error: {exc}")
            return
        self.out(self.display.format_order_report(
            order, rider, start_pos, trip_distance, estimated, actual,
            bool(recruited)))
        self.out(self.display.render_map(self.system.riders(), [order], trip))

    def cmd_status(self, _args: List[str]) -> None:
        """Show funds and every rider's state."""
        self.out(self.display.format_status(
            self.system.get_funds(), self.system.riders(), self.system.current_time()))

    def cmd_orders(self, _args: List[str]) -> None:
        """Show details of all orders."""
        self.out(self.display.format_orders(self.system.all_orders()))

    def cmd_riders(self, _args: List[str]) -> None:
        """Show every recorded rider status change."""
        self.out(self.display.format_rider_log(self.system.riders()))

    def cmd_map(self, _args: List[str]) -> None:
        """Show the ASCII map with riders and active orders."""
        active = [o for o in self.system.all_orders() if o.status != "completed"]
        self.out(self.display.render_map(self.system.riders(), active))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation clock."""
        count = self.inp.parse_tick_count(args)
        for _ in range(count):
            self.system.tick()
        self.out(f"Advanced {count} tick(s). Time is now {self.system.current_time()}.")

    def cmd_save(self, args: List[str]) -> None:
        """Persist the system state to a JSON file."""
        path = args[0] if args else config.DEFAULT_STATE_PATH
        try:
            self.system.save_state(path)
            self.out(f"State saved to {path}")
        except OSError as exc:
            self.out(f"Error: could not save state: {exc}")

    def cmd_history(self, _args: List[str]) -> None:
        """Print the command history."""
        if not self.inp.history:
            self.out("History is empty.")
            return
        for index, entry in enumerate(self.inp.history, start=1):
            self.out(f"  {index:>3}  {entry}")

    def cmd_help(self, _args: List[str]) -> None:
        """Print the command reference."""
        self.out(self.display.format_help())

    def cmd_quit(self, _args: List[str]) -> None:
        """Stop the main loop."""
        self.system.stop()
        self.out("Goodbye.")

    def run(self) -> int:
        """Run the interactive main loop until quit or end of input.

        Returns:
            Process exit code (0 on normal exit).
        """
        self.out(BANNER)
        while globalvar.get_value("running", True):
            try:
                name, args = self.inp.read_command()
            except CommandError as exc:
                self.out(f"Error: {exc}")
                continue
            except (EOFError, KeyboardInterrupt):
                self.out("\nExiting.")
                break
            if not name:
                continue
            try:
                self.handle(name, args)
            except CommandError as exc:
                self.out(f"Error: {exc}")
            except Exception as exc:  # Error recovery: keep the simulator alive.
                logger.exception("Unexpected error while handling '%s'", name)
                self.out(f"Unexpected error: {exc}. Attempting state recovery...")
                for fix in self.system.check_consistency():
                    self.out(f"  recovered: {fix}")
        return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Configure logging and run the dispatch application.

    Args:
        argv: Unused placeholder for future argument parsing.

    Returns:
        Process exit code.
    """
    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = DispatchApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
