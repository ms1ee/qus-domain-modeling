"""Command-line entry point for the food delivery dispatch simulator.

Run with:  python src/main.py
"""

import logging
import os
import sys
from typing import Callable, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from display import DisplayManager  # noqa: E402
from input_manager import InputError, InputManager  # noqa: E402
from settings import CONFIG, load_config  # noqa: E402
from system import SystemManager, init_system  # noqa: E402

CONFIG_FILE = "dispatch_config.json"
STATE_FILE = "dispatch_state.json"
LOG_FILE = "dispatch.log"
MAX_TICKS_PER_COMMAND = 1000

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy]  (s)   Create an order: restaurant x y, customer x y (0-800).
                             Prompts for the four values if none are given.
  status               (st)  System funds, time, and every rider's state and orders.
  orders               (o)   Table of all orders with timing and assigned rider.
  riders               (r)   Full status-change log for every rider.
  map                  (m)   ASCII map with riders and active orders.
  tick [n]             (t)   Advance the simulation by n ticks (default 1).
  history              (h)   List previously entered commands.
  !!  /  !n                  Re-run the last command / command number n.
  save [file]          (sv)  Save config, riders and orders as JSON.
  help                 (?)   Show this help.
  quit / exit          (q/x) Leave the simulator.
"""


def setup_logging() -> None:
    """Send log output to a file so the console stays clean."""
    try:
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            encoding="utf-8",
        )
    except OSError:
        logging.basicConfig(level=logging.WARNING)


class App:
    """Binds the system, display and input manager to command handlers."""

    def __init__(self, system: SystemManager, display: DisplayManager,
                 inputs: InputManager) -> None:
        self.system = system
        self.display = display
        self.inputs = inputs
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
            "exit": self.cmd_quit,
        }

    def dispatch(self, command: str, args: List[str]) -> None:
        """Run the handler for a canonical command name."""
        self._handlers[command](args)

    def cmd_start(self, args: List[str]) -> None:
        """Create an order, assign it, and show the rider's route on the map."""
        tokens = list(args)
        if not tokens:
            prompt = "Enter restaurant x, restaurant y, customer x, customer y: "
            tokens = self.inputs.read_line(prompt).replace(",", " ").split()
        rx, ry, cx, cy = self.inputs.parse_coordinates(tokens)
        result = self.system.submit_order((rx, ry), (cx, cy))
        order = result["order"]
        rider = result["rider"]
        new_riders = result["new_riders"]

        print(f"Order #{order.id} created at t={order.start_time}")
        print(f"  Restaurant: input ({rx},{ry}) -> grid cell "
              f"({order.res_pos.grid_x},{order.res_pos.grid_y}), center {order.res_pos.center}")
        print(f"  Customer  : input ({cx},{cy}) -> grid cell "
              f"({order.cus_pos.grid_x},{order.cus_pos.grid_y}), center {order.cus_pos.center}")
        if new_riders:
            ids = ", ".join(f"#{r.rider_id}" for r in new_riders)
            print(f"  New rider added: YES ({ids})")
        else:
            print(f"  New rider added: NO (funds {self.system.funds}, "
                  f"hire threshold {CONFIG['hire_threshold']})")

        if rider is None:
            print("  No rider is available. The order is queued and will be assigned "
                  "when a rider has capacity.")
            return

        route = result["route"]
        print(f"  Assigned to rider #{rider.rider_id} (speed {rider.speed} units/tick, "
              f"state: {rider.status_name})")
        print(f"  Route: {route.total_distance} units, estimated {route.estimated_ticks} ticks")
        print(self.display.render_map([rider], [order], route))

    def cmd_status(self, _args: List[str]) -> None:
        """Print the system snapshot and every rider's state."""
        system = self.system
        print(self.display.render_status(
            funds=system.funds,
            simulated_time=system.simulated_time,
            riders=system.riders,
            pending=len(system.order_manager.pending),
            active=len(system.order_manager.active),
            completed=len(system.order_manager.completed),
        ))

    def cmd_orders(self, _args: List[str]) -> None:
        """Print the order table."""
        print(self.display.render_orders(self.system.order_manager.orders))

    def cmd_riders(self, _args: List[str]) -> None:
        """Print every recorded rider status change."""
        print(self.display.render_rider_logs(self.system.riders))

    def cmd_map(self, _args: List[str]) -> None:
        """Print the ASCII map with riders and active orders."""
        print(self.display.render_map(self.system.riders,
                                      self.system.order_manager.active))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation and report any deliveries."""
        count = self.inputs.parse_tick_count(args, MAX_TICKS_PER_COMMAND)
        delivered = self.system.tick(count)
        print(f"Advanced {count} tick(s). Simulated time: t={self.system.simulated_time}")
        if not delivered:
            print("  No deliveries completed.")
        for order in delivered:
            print(self.display.render_delivery(order))

    def cmd_history(self, _args: List[str]) -> None:
        """List previously entered commands."""
        history = self.inputs.command_history
        if not history:
            print("No commands in history.")
            return
        for index, line in enumerate(history, start=1):
            print(f"  {index:>3}  {line}")

    def cmd_save(self, args: List[str]) -> None:
        """Save the state to a JSON file."""
        path = args[0] if args else STATE_FILE
        try:
            saved = self.system.save_state(path)
        except OSError as exc:
            print(f"Could not save state: {exc}")
            return
        print(f"State saved to {saved}")

    def cmd_help(self, _args: List[str]) -> None:
        """Print the command reference."""
        print(HELP_TEXT)

    def cmd_quit(self, _args: List[str]) -> None:
        """Stop the main loop."""
        self.system.running_state = False


def run() -> int:
    """Run the interactive command loop.

    Returns:
        Process exit code (0 on normal exit).
    """
    setup_logging()
    load_config(CONFIG_FILE)
    system = init_system()
    app = App(system, DisplayManager(), InputManager())

    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while system.running_state:
        try:
            line = app.inputs.read_line()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        try:
            line = app.inputs.expand_history(line)
            app.inputs.record(line)
            command, args = app.inputs.parse(line)
            app.dispatch(command, args)
            problems = system.verify_consistency()
            if problems:
                logger.warning("Consistency problems: %s", problems)
                system.repair()
        except InputError as exc:
            print(f"Input error: {exc}")
        except ValueError as exc:
            print(f"Invalid value: {exc}")
        except Exception as exc:  # noqa: BLE001 - keep the console alive
            logger.exception("Unexpected error while handling %r", line)
            print(f"Unexpected error: {exc}. Attempting state recovery...")
            actions = system.repair()
            for action in actions:
                print(f"  recovery: {action}")
    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
