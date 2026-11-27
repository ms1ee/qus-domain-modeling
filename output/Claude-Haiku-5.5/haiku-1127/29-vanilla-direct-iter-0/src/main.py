"""Command-line entry point for the food delivery dispatch simulator."""

import logging
import os
import sys

from display import DisplayManager
from globalvar import get_value
from grid import MAX_ROUTE_TICKS
from input_manager import HELP_TEXT, InputManager
from order import OrderManager
from system import SystemManager, init_system, load_config, save_snapshot

logger = logging.getLogger("dispatch")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SNAPSHOT_PATH = os.path.join(BASE_DIR, "snapshot.json")
MAX_WAIT_TICKS = 1000

BANNER = """==============================================
 Food Delivery Order Dispatch Simulator (8x8 grid)
 Type 'help' for commands.
=============================================="""


class DispatchApp:
    """Ties together the managers and runs the interactive command loop."""

    def __init__(self, reader=None, writer=print) -> None:
        """Initialise system state and collaborators.

        Args:
            reader: Optional callable used to read input lines.
            writer: Callable used to output text.
        """
        init_system()
        load_config(CONFIG_PATH)
        self.system = SystemManager()
        self.orders = OrderManager()
        self.display = DisplayManager()
        self.inputs = InputManager(reader)
        self.out = writer
        self.handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "wait": self.cmd_wait,
            "history": self.cmd_history,
            "save": self.cmd_save,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    def run(self) -> None:
        """Run the main loop until the user quits or input ends."""
        self.out(BANNER)
        while self.system.is_running:
            try:
                line = self.inputs.read_command("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self.out("")
                break
            except ValueError as exc:
                self.out(f"Error: {exc}")
                continue
            if line is None:
                continue
            name, args = self.inputs.parse_command(line)
            handler = self.handlers.get(name)
            if handler is None:
                self.out(f"Unknown command '{name}'. Type 'help' for a list.")
                continue
            try:
                handler(args)
            except ValueError as exc:
                self.out(f"Input error: {exc}")
            except Exception:  # keep the system running on unexpected errors
                logger.exception("Unexpected error in command %s", name)
                self.out("An unexpected error occurred; system state kept.")
        self.out("Goodbye.")

    def cmd_start(self, args) -> None:
        """Create an order, recruit if needed, assign it and simulate delivery."""
        if args:
            coords = self.inputs.parse_coordinates(args)
        else:
            coords = self.inputs.prompt_coordinates()
        if coords is None:
            self.out("Order cancelled.")
            return

        order = self.orders.create_order(*coords)
        created = self.system.recruit_if_needed(
            len(self.orders.pending_orders()))
        for rider in created:
            self.out(f"New rider #{rider.rider_id} recruited "
                     f"(funds now {self.system.funds}).")

        rider = self.orders.assign(order)
        if rider is None:
            self.out("No rider available; order remains pending.")
            return

        route = [rider.position]
        ticks = 0
        while order.status != "completed" and ticks < MAX_ROUTE_TICKS:
            self.system.tick()
            ticks += 1
            route.append(rider.position)
        if order.status != "completed":
            self.out("Warning: delivery did not finish within the tick limit.")

        self.out(self.display.format_assignment(
            order, rider, bool(created), route, ticks))
        self.out(self.display.render_map(
            riders=self.system.riders(), orders=[order], route=route))

    def cmd_status(self, _args) -> None:
        """Show funds, riders and the current map."""
        self.out(self.display.format_status())
        self.out(self.display.render_map())

    def cmd_orders(self, _args) -> None:
        """Show every order."""
        self.out(self.display.format_orders())

    def cmd_riders(self, _args) -> None:
        """Show the status-change log for every rider."""
        self.out(self.display.format_rider_logs())

    def cmd_wait(self, args) -> None:
        """Advance simulated time by a number of ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"'{args[0]}' is not an integer") from None
        if count < 1 or count > MAX_WAIT_TICKS:
            raise ValueError(f"tick count must be between 1 and "
                             f"{MAX_WAIT_TICKS}")
        for _ in range(count):
            self.system.tick()
        self.out(f"Advanced {count} tick(s); now at tick "
                 f"{get_value('tick', 0)}.")

    def cmd_history(self, _args) -> None:
        """Print the command history."""
        if not self.inputs.history:
            self.out("No commands yet.")
            return
        for index, command in enumerate(self.inputs.history, start=1):
            self.out(f"{index:>4}  {command}")

    def cmd_save(self, args) -> None:
        """Save a JSON snapshot of the system state."""
        path = args[0] if args else SNAPSHOT_PATH
        try:
            save_snapshot(path)
            self.out(f"Snapshot saved to {path}")
        except OSError as exc:
            self.out(f"Could not save snapshot: {exc}")

    def cmd_help(self, _args) -> None:
        """Print the command help."""
        self.out(HELP_TEXT)

    def cmd_quit(self, _args) -> None:
        """Stop the main loop."""
        self.system.stop()


def main() -> int:
    """Program entry point.

    Returns:
        Process exit code.
    """
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = DispatchApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
