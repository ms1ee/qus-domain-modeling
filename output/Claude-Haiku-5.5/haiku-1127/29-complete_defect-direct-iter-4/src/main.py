"""Entry point and interactive command loop for the dispatch simulator.

Run with:  python src/main.py [config.json]
Each loop iteration is one command; simulated time (ticks) advances via the
'tick' command (or an empty line).
"""

import logging
import os
import sys
from typing import Callable, Dict, List, Optional, Sequence

from display import DisplayManager
from input_manager import HELP_TEXT, CommandError, InputManager
from path_planner import PathPlanner, grid_cell, manhattan
from system import SystemManager

try:
    import readline  # noqa: F401  (arrow-key history where available)
except ImportError:  # pragma: no cover - e.g. Windows without pyreadline
    pass

logger = logging.getLogger("dispatch")

DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_SAVE_FILE = "state.json"


class Application:
    """Interactive application wiring SystemManager, InputManager and DisplayManager."""

    def __init__(self, system: SystemManager, reader: Callable[[str], str] = input,
                 output: Callable[..., None] = print) -> None:
        """Create the application.

        Args:
            system: The initialised SystemManager.
            reader: Function used to read input lines.
            output: Function used to print output.
        """
        self.system = system
        self.display = DisplayManager()
        self.inp = InputManager(reader)
        self.planner = PathPlanner()
        self._print = output
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
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

    def run(self) -> int:
        """Run the interactive loop until quit or end of input.

        Returns:
            Process exit code (0 on normal exit).
        """
        self._print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.is_running():
            try:
                line = self.inp.read_line(f"[t={self.system.current_time}] > ")
            except (EOFError, KeyboardInterrupt):
                self._print("")
                break
            try:
                command, args = self.inp.resolve(line)
                self._handlers[command](args)
            except CommandError as exc:
                self._print(f"Error: {exc}")
            except Exception as exc:  # noqa: BLE001 - keep the session alive
                logger.exception("Unexpected failure handling %r", line)
                self._print(f"Unexpected internal error: {exc}. "
                            "System state was preserved.")
        self._print("Goodbye.")
        return 0

    def _prompt_coordinates(self) -> List[str]:
        """Ask the user for four coordinates interactively."""
        line = self.inp.read_line(
            "Enter restaurant_x restaurant_y customer_x customer_y: ")
        return line.split()

    def cmd_start(self, args: List[str]) -> None:
        """Place an order, recruit if funded, assign and show the route."""
        if not self.system.can_accept_order():
            raise CommandError(
                f"No riders and funds {self.system.funds} are below the hire "
                f"threshold {self.system.config['hire_threshold']}; order rejected.")
        tokens = args if args else self._prompt_coordinates()
        coords = InputManager.parse_coordinates(tokens)
        res_pos = (coords[0], coords[1])
        cus_pos = (coords[2], coords[3])

        new_rider = self.system.try_recruit()
        order = self.system.orders.create_order(res_pos, cus_pos)
        rider = self.system.orders.assign_order(order)

        route = self.planner.plan(rider.position, order.res_pos)
        route += self.planner.plan(order.res_pos, order.cus_pos)[1:]
        length = PathPlanner.route_length(route)
        eta = -(-length // rider.speed)  # ceiling division
        queued = len(rider.orders) - 1

        self._print(f"Order #{order.id} accepted.")
        self._print(f"Restaurant: grid cell {order.restaurant_cell} "
                    f"(center {order.res_pos})")
        self._print(f"Customer:   grid cell {order.customer_cell} "
                    f"(center {order.cus_pos})")
        if new_rider is not None:
            self._print(f"New rider added: Rider #{new_rider.rider_id} "
                        f"(funds now {self.system.funds}).")
        else:
            self._print(f"No new rider added (funds {self.system.funds}).")
        self._print(f"Assigned to Rider #{rider.rider_id} ({rider.state_name}, "
                    f"speed {rider.speed} units/tick).")
        self._print(f"Route length {length} units, estimated {eta} tick(s)"
                    + (f"; {queued} order(s) queued ahead." if queued > 0 else "."))
        self._print(self.display.render_map(self.system.riders,
                                            self.system.orders.active_orders(),
                                            route))

    def cmd_status(self, args: List[str]) -> None:
        """Show the system status snapshot."""
        active = self.system.orders.active_orders()
        completed = self.system.orders.completed_orders()
        self._print(self.display.format_status(self.system.funds, self.system.current_time,
                                               self.system.riders, len(active),
                                               len(completed)))

    def cmd_orders(self, args: List[str]) -> None:
        """Show details for all orders."""
        self._print(self.display.format_orders(self.system.orders.all_orders()))

    def cmd_riders(self, args: List[str]) -> None:
        """Show every rider's recorded status changes."""
        self._print(self.display.format_riders(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map with riders and active orders."""
        self._print(self.display.render_map(self.system.riders,
                                            self.system.orders.active_orders()))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance simulated time and report resulting rider events."""
        steps = InputManager.parse_tick_count(args)
        riders = self.system.riders
        marks = {rider.rider_id: len(rider.history) for rider in riders}
        self.system.tick(steps)
        for issue in self.system.check_consistency():
            self._print(f"Warning: {issue}")
        events = []
        for rider in riders:
            events.extend(rider.history[marks.get(rider.rider_id, 0):])
        events.sort(key=lambda e: (e["time"], e["rider_id"]))
        self._print(f"Advanced {steps} tick(s); time is now t={self.system.current_time}.")
        self._print(self.display.format_events(events))

    def cmd_history(self, args: List[str]) -> None:
        """Show the command history with indices for '!N' shortcuts."""
        if not self.inp.history:
            self._print("History is empty.")
            return
        for index, entry in enumerate(self.inp.history, start=1):
            self._print(f"{index:>4}  {entry}")

    def cmd_save(self, args: List[str]) -> None:
        """Save a JSON snapshot of the system state."""
        path = args[0] if args else DEFAULT_SAVE_FILE
        try:
            self.system.save(path)
        except OSError as exc:
            raise CommandError(f"Could not save to {path}: {exc}") from exc
        self._print(f"State saved to {path}.")

    def cmd_help(self, args: List[str]) -> None:
        """Show the command reference."""
        self._print(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.stop()


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Command-line arguments (without the program name). The first
            argument, if present, is the configuration file path.

    Returns:
        Process exit code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        filename="dispatch.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args:
        config_path: Optional[str] = args[0]
    elif os.path.exists(DEFAULT_CONFIG_FILE):
        config_path = DEFAULT_CONFIG_FILE
    else:
        config_path = None
    try:
        system = SystemManager(config_path)
    except (OSError, ValueError) as exc:
        print(f"Startup failed: {exc}")
        return 1
    return Application(system).run()


if __name__ == "__main__":
    sys.exit(main())
