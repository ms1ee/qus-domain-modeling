"""Command-line entry point for the food delivery dispatch simulator.

Run with:  python src/main.py
"""

import logging
import math
import sys

import globalvar
from config import load_config, save_state, snapshot_state
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from order_model import COMPLETED
from path_planner import MAP_SIZE, route_length
from rider import STATE_NAMES
from system import SystemManager, init_system

LOG_FILE = "dispatch.log"
MAX_TICKS_PER_COMMAND = 10000

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy]  [s]  Create an order (restaurant then customer, 0-800).
                            Without arguments you will be prompted.
  status               [st] Show system funds, riders and their orders.
  orders               [o]  Show all orders with timing and distance.
  riders               [r]  Show every rider status change log.
  map                  [m]  Show the ASCII street map.
  tick [n]             [t]  Advance the simulation by n ticks (default 1).
  save                 [w]  Save state to the JSON state file.
  history              Show previously entered commands.
  help                 [h]  Show this help.
  quit                 [q]  Exit (also: exit)."""


class DispatchApp:
    """Interactive application that wires managers together and runs the loop."""

    def __init__(self, config):
        """Initialise the system and all managers.

        Args:
            config: Configuration dict produced by ``load_config``.
        """
        init_system()
        globalvar.set_value("funds", int(config["initial_funds"]))
        globalvar.set_value("rider_speed", int(config["rider_speed"]))
        globalvar.set_value("recruit_min_funds", int(config["recruit_min_funds"]))
        globalvar.set_value("recruit_cost", int(config["recruit_cost"]))
        self.state_file = str(config["state_file"])
        self.system = SystemManager()
        self.orders = OrderManager(self.system)
        self.display = DisplayManager()
        self.inputs = InputManager()
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
        }

    def run(self):
        """Run the interactive main loop until quit or end of input."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands.")
        while self.system.is_running():
            try:
                line = self.inputs.read_line("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            try:
                self.execute(line)
            except EOFError:
                print()
                break
            except ValueError as exc:
                print(f"Error: {exc}")
            except Exception:
                logger.exception("Unexpected error while executing %r", line)
                print("Internal error: the command was aborted, state was kept. "
                      f"See {LOG_FILE} for details.")
                self._recover()
            self._report_inconsistencies()
        print("Goodbye.")

    def execute(self, line):
        """Parse and run one command line.

        Args:
            line: Raw user input.
        """
        command, args = self.inputs.parse(line)
        if command is None:
            return
        self._handlers[command](args)

    def cmd_start(self, args):
        """Create an order, dispatch it, and show the assigned rider's route."""
        if args:
            coords = InputManager.parse_coordinates(args)
        else:
            coords = self.inputs.prompt_order()
            if coords is None:
                print("Order entry cancelled.")
                return
        rx, ry, cx, cy = coords
        result = self.orders.place_order((rx, ry), (cx, cy))
        order = result["order"]
        rider = result["rider"]
        new_riders = result["new_riders"]
        now = globalvar.get_value("time")

        print(f"Order #{order.id} created at tick {now}.")
        print(f"  Restaurant grid location: ({order.restaurant[0]}, {order.restaurant[1]})")
        print(f"  Customer grid location:   ({order.customer[0]}, {order.customer[1]})")
        if new_riders:
            ids = ", ".join(f"#{rid}" for rid in new_riders)
            print(f"  New rider added: yes (Rider {ids})")
        else:
            print("  New rider added: no")

        if rider is None:
            print("  No rider available (insufficient funds). The order is pending "
                  "and will be retried every tick.")
            return

        print(f"  Assigned to Rider #{rider.rider_id} "
              f"(status: {STATE_NAMES[rider.state]}, "
              f"active orders: {rider.active_order_count()})")
        route = rider.route_to_order(order)
        distance = route_length(route)
        ticks = math.ceil(distance / rider.speed) if rider.speed > 0 else 0
        print(f"  Speed: {rider.speed} units/tick   Route length: {distance} units   "
              f"Estimated time: {ticks} tick(s)")
        print(self.display.render_map(riders=[rider], active_orders=[order], route=route))

    def cmd_status(self, args):
        """Show the system status snapshot."""
        riders = globalvar.get_value("riders")
        pending = globalvar.get_value("pending_orders")
        print(f"Time: tick {globalvar.get_value('time')}")
        print(self.display.render_status(self.system.get_funds(), riders, len(pending)))

    def cmd_orders(self, args):
        """Show the full order table."""
        print(self.display.render_orders(globalvar.get_value("orders")))

    def cmd_riders(self, args):
        """Show the rider status change logs."""
        print(self.display.render_rider_logs(globalvar.get_value("riders")))

    def cmd_map(self, args):
        """Show the ASCII map with riders and active orders."""
        orders = globalvar.get_value("orders")
        active = [o for o in orders if o.status != COMPLETED]
        print(self.display.render_map(riders=globalvar.get_value("riders"),
                                      active_orders=active))

    def cmd_tick(self, args):
        """Advance the simulation by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"'{args[0]}' is not an integer tick count")
            if not 1 <= count <= MAX_TICKS_PER_COMMAND:
                raise ValueError(f"tick count must be between 1 and {MAX_TICKS_PER_COMMAND}")
        for _ in range(count):
            self._step()
        print(f"Time is now tick {globalvar.get_value('time')}. "
              f"Riders: {len(globalvar.get_value('riders'))}, "
              f"pending orders: {len(globalvar.get_value('pending_orders'))}.")

    def cmd_save(self, args):
        """Save the system state to the JSON state file."""
        try:
            save_state(self.state_file, snapshot_state())
        except OSError as exc:
            raise ValueError(f"could not save state: {exc}")
        print(f"State saved to {self.state_file}.")

    def cmd_history(self, args):
        """Print the command history of this session."""
        if not self.inputs.history:
            print("No commands entered yet.")
            return
        for index, entry in enumerate(self.inputs.history, start=1):
            print(f"  {index:>3}  {entry}")

    def cmd_help(self, args):
        """Print the command reference."""
        print(HELP_TEXT)

    def cmd_quit(self, args):
        """Stop the main loop."""
        self.system.stop()

    def _step(self):
        """Run one simulation tick: dispatch pending orders, then move riders."""
        assigned, new_riders = self.orders.dispatch_pending()
        for rider_id in new_riders:
            print(f"  [t={globalvar.get_value('time')}] Rider #{rider_id} recruited.")
        for order in assigned:
            print(f"  [t={globalvar.get_value('time')}] Order #{order.id} "
                  f"assigned to Rider #{order.rider_id}.")
        self.system.tick()

    def _recover(self):
        """Attempt to restore consistency after an unexpected error."""
        try:
            self.orders.dispatch_pending()
        except Exception:
            logger.exception("Recovery dispatch failed")

    def _report_inconsistencies(self):
        """Log and display any consistency problems detected in the state."""
        for issue in self.system.check_consistency():
            logger.warning("Consistency issue: %s", issue)
            print(f"Warning: {issue}")


def _configure_logging():
    """Configure file logging, falling back to stderr if the file is unusable."""
    log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    try:
        logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format=log_format)
    except OSError:
        logging.basicConfig(stream=sys.stderr, level=logging.WARNING, format=log_format)


def main():
    """Program entry point.

    Returns:
        Process exit code.
    """
    _configure_logging()
    config = load_config()
    app = DispatchApp(config)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
