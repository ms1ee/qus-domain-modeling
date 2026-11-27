"""Command-line entry point for the food delivery dispatch simulator.

Each iteration of the main loop processes one command and then advances the
simulation by one tick.
"""

import logging
import math
import sys

import globalvar
import grid
from display import DisplayManager
from input_manager import InputManager
from path_planner import PathPlanner
from system import SystemManager, init_system

CONFIG_PATH = "config.json"
STATE_PATH = "dispatch_state.json"
LOG_PATH = "dispatch.log"
MAX_TICK_COMMAND = 1000

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] [a]  Place an order: restaurant then customer grid
                           coordinates (0-800). Prompts if omitted.
  status [s]               Funds, rider count and each rider's state/orders.
  orders [o]               Details of all orders.
  riders [r]               Status-change log of every rider.
  map [m]                  ASCII map of riders and active orders.
  tick [t] [n]             Advance the simulation by n extra ticks (default 1).
  save [v] [path]          Save state to JSON (default dispatch_state.json).
  history [y]              Show command history. Use !! or !n to repeat.
  help [h, ?]              Show this help.
  quit [q] / exit [x]      Leave the program.
Every command is followed by one simulation tick."""


class DispatchApp:
    """Interactive controller that wires the modules together."""

    def __init__(self, reader=input, writer=print):
        """Create the application.

        Args:
            reader: Callable used to read input lines.
            writer: Callable used to print output lines.
        """
        self.system = SystemManager()
        self.inputs = InputManager(reader)
        self.display = DisplayManager()
        self.planner = PathPlanner()
        self._out = writer
        self._log = logging.getLogger("dispatch.app")
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

    def say(self, text=""):
        """Print a line of output."""
        self._out(text)

    def startup(self):
        """Initialise the system, load configuration and recruit if able."""
        init_system()
        self.system.load_config(CONFIG_PATH)
        rider = self.system.try_recruit()
        self.say("=== Food Delivery Dispatch Simulator ===")
        if rider is not None:
            self.say(f"Funds reached the hiring threshold. "
                     f"Rider #{rider.rider_id} recruited.")
        self.say("Type 'help' for commands.")

    def run(self):
        """Run the main loop until the system is stopped."""
        self.startup()
        while self.system.running:
            try:
                line = self.inputs.read_line()
            except (EOFError, KeyboardInterrupt):
                self.say()
                break
            self.execute(line)
            if self.system.running:
                self._safe_tick()
        self.say("Goodbye.")

    def _safe_tick(self):
        """Advance one tick, recovering from unexpected errors."""
        try:
            self.system.tick()
        except Exception:  # noqa: BLE001 - keep the simulation alive
            self._log.exception("Error during simulation tick")
            self.say("Internal error during tick; state has been kept.")

    def execute(self, line):
        """Expand, validate and dispatch one command line.

        Args:
            line: Raw command line typed by the user.
        """
        try:
            expanded = self.inputs.expand_history(line)
        except IndexError as exc:
            self.say(f"History error: {exc}")
            return
        if not expanded:
            return
        self.inputs.record(expanded)
        try:
            name, args = self.inputs.parse_command(expanded)
        except ValueError as exc:
            self.say(f"Error: {exc}")
            return
        if name is None:
            return
        handler = self._handlers[name]
        try:
            handler(args)
        except EOFError:
            raise
        except Exception as exc:  # noqa: BLE001 - graceful recovery
            self._log.exception("Command '%s' failed", name)
            self.say(f"Error while running '{name}': {exc}")

    def cmd_start(self, args):
        """Handle ``start``: create an order and assign a rider."""
        if args:
            try:
                coords = self.inputs.parse_coordinates(args)
            except ValueError as exc:
                self.say(f"Invalid input: {exc}")
                return
        else:
            self.say("Enter restaurant and customer coordinates (0-800).")
            coords = self.inputs.prompt_coordinates(self.say)
            if coords is None:
                self.say("Order cancelled.")
                return

        rx, ry, cx, cy = coords
        new_rider = self.system.try_recruit()
        order = self.system.orders.create_order((rx, ry), (cx, cy))
        self.say(f"Order #{order.id} created.")
        self.say(f"  Restaurant: input ({rx}, {ry}) -> grid {order.res_grid}")
        self.say(f"  Customer:   input ({cx}, {cy}) -> grid {order.cus_grid}")
        if new_rider is not None:
            self.say(f"New rider #{new_rider.rider_id} added to the team.")

        rider = self.system.orders.assign(order)
        if rider is None:
            self.say("No rider available. The order is queued (pending).")
            return
        route = self.planner.plan_route(rider.position,
                                        [order.res_grid, order.cus_grid])
        distance = grid.path_length(rider.position, route)
        ticks = math.ceil(distance / rider.speed) if distance else 0
        self.say(self.display.render_assignment(
            rider, order, route, distance, ticks))

    def cmd_status(self, _args):
        """Handle ``status``: show funds, riders and pending orders."""
        self.say(self.display.render_status(
            self.system.funds, self.system.riders,
            len(self.system.orders.pending), self.system.tick_count))

    def cmd_orders(self, _args):
        """Handle ``orders``: show the order table."""
        self.say(self.display.render_orders(self.system.orders.get_all_orders()))

    def cmd_riders(self, _args):
        """Handle ``riders``: show every rider's status-change log."""
        self.say(self.display.render_rider_logs(self.system.riders))

    def cmd_map(self, _args):
        """Handle ``map``: show the ASCII map."""
        self.say(self.display.render_map(self.system.riders,
                                         self.system.orders.active))

    def cmd_tick(self, args):
        """Handle ``tick [n]``: advance the simulation by n extra ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                self.say("Invalid input: tick count must be an integer.")
                return
            if count < 1 or count > MAX_TICK_COMMAND:
                self.say(f"Tick count must be between 1 and "
                         f"{MAX_TICK_COMMAND}.")
                return
        for _ in range(count):
            self._safe_tick()
        self.say(f"Advanced {count} tick(s). Current tick: "
                 f"{self.system.tick_count}.")

    def cmd_save(self, args):
        """Handle ``save [path]``: persist the current state."""
        path = args[0] if args else STATE_PATH
        if self.system.save_state(path):
            self.say(f"State saved to {path}.")
        else:
            self.say(f"Could not save state to {path}. See dispatch.log.")

    def cmd_history(self, _args):
        """Handle ``history``: list previously entered commands."""
        if not self.inputs.history:
            self.say("History is empty.")
            return
        for index, entry in enumerate(self.inputs.history, start=1):
            self.say(f"  {index:>3}  {entry}")

    def cmd_help(self, _args):
        """Handle ``help``: show the command reference."""
        self.say(HELP_TEXT)

    def cmd_quit(self, _args):
        """Handle ``quit``/``exit``: stop the main loop."""
        self.system.stop()


def main():
    """Configure logging and run the interactive application.

    Returns:
        int: Process exit code.
    """
    try:
        logging.basicConfig(
            filename=LOG_PATH,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    except OSError:
        logging.basicConfig(level=logging.WARNING)
    app = DispatchApp()
    try:
        app.run()
    except Exception:  # noqa: BLE001 - last-resort reporting
        logging.getLogger("dispatch.app").exception("Fatal error")
        print("A fatal error occurred. See dispatch.log for details.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
