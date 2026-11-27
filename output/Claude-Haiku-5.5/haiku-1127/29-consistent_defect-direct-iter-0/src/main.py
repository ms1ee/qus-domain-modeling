"""Command-line entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [config.json]
"""

import logging
import math
import os
import sys

import globalvar
from display import DisplayManager
from input_manager import InputError, InputManager
from order import OrderManager
from path_planner import PathPlanner
from system import init_system

logger = logging.getLogger("dispatch")

BANNER = (
    "Food Delivery Order Dispatch Simulator\n"
    "Type 'help' for commands. Map: 800x800 units, 8x8 cells."
)

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant then customer, 0-1000).
                       Without arguments you will be prompted.
  status (s)           System funds, riders and their order lists.
  orders (o)           Details for all orders.
  riders (r)           Status change log for every rider.
  tick [n] (t)         Advance simulated time by n ticks (default 1).
  map (m)              Show the ASCII map with riders and orders.
  save [path]          Save state to JSON (default simulation_state.json).
  help (h, ?)          Show this help.
  quit (q) / exit (e)  Leave the program.
  !!  and  !n          Repeat the last command / history entry n."""


class SimulatorApp:
    """Interactive REPL tying together all simulator modules."""

    def __init__(self, system, inputs=None):
        """Create the application.

        Args:
            system: SystemManager instance.
            inputs: Optional InputManager (defaults to a new one).
        """
        self.system = system
        self.orders = OrderManager(system)
        self.inputs = inputs or InputManager()
        self.display = DisplayManager()
        self._handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "tick": self.cmd_tick,
            "map": self.cmd_map,
            "save": self.cmd_save,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    def run(self):
        """Run the main command loop until the user quits."""
        print(BANNER)
        while self.system.running:
            try:
                line = self.inputs.read_line()
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.stop()
                break
            try:
                command, args = self.inputs.parse(line)
            except InputError as exc:
                print("Error: %s" % exc)
                continue
            if command is None:
                continue
            try:
                self._handlers[command](args)
            except EOFError:
                self.system.stop()
                break
            except (InputError, ValueError) as exc:
                print("Error: %s" % exc)
            except Exception:  # error recovery: keep the session alive
                logger.exception("Unexpected failure in command '%s'", command)
                print("Unexpected internal error; state preserved. "
                      "See log for details.")
        print("Goodbye.")

    def cmd_start(self, args):
        """Create an order, dispatch it and show the rider route map.

        Args:
            args: Optional four coordinate tokens.
        """
        coords = (self.inputs.parse_coordinates(args) if args
                  else self.inputs.prompt_coordinates())
        order = self.orders.create_order(coords)
        rider, recruited = self.orders.dispatch(order)

        print("Order #%d created at tick %d." % (order.id, order.start_time))
        print("Restaurant grid point: %s (cell %s)"
              % (order.res_pos, PathPlanner.grid_cell(*order.res_pos)))
        print("Customer grid point:   %s (cell %s)"
              % (order.cus_pos, PathPlanner.grid_cell(*order.cus_pos)))
        if recruited:
            print("New rider added: yes (rider %d)"
                  % self.system.riders[-1].rider_id)
        else:
            print("New rider added: no")

        if rider is None:
            print("No rider available. The order stays pending and will be "
                  "assigned when a rider frees up.")
            return

        print("Assigned to rider %d (state: %s, active orders: %d)"
              % (rider.rider_id, rider.state_name, rider.active_order_count()))
        route = PathPlanner.plan_route(rider.position,
                                       rider.remaining_waypoints())
        distance = PathPlanner.route_length(route)
        ticks = math.ceil(distance / rider.speed) if rider.speed else 0
        print("Speed: %d units/tick | Route distance: %d units | "
              "Estimated time: %d ticks" % (rider.speed, distance, ticks))
        print(self.display.render_map(riders=[rider],
                                      orders=self.orders.all_orders(),
                                      route=route))

    def cmd_status(self, _args):
        """Print the system status snapshot."""
        print(self.display.render_status(self.system, self.system.riders))

    def cmd_orders(self, _args):
        """Print all order details."""
        print(self.display.render_orders(self.orders.all_orders()))

    def cmd_riders(self, _args):
        """Print the status change log for all riders."""
        print(self.display.render_rider_log(self.system.riders))

    def cmd_tick(self, args):
        """Advance the simulation.

        Args:
            args: Optional tick count.
        """
        count = 1
        if args:
            count = InputManager.parse_int(args[0], "tick count")
            if not 1 <= count <= 1000:
                raise InputError("tick count must be between 1 and 1000.")
        for _ in range(count):
            self.orders.retry_pending()
            self.system.tick()
        print("Simulated time is now tick %d (%d riders, %d pending orders)."
              % (self.system.tick_count, len(self.system.riders),
                 self.orders.unassigned_count()))

    def cmd_map(self, _args):
        """Print the ASCII map with riders and active orders."""
        print(self.display.render_map(riders=self.system.riders,
                                      orders=self.orders.all_orders()))

    def cmd_save(self, args):
        """Save the simulation state to JSON.

        Args:
            args: Optional output path.
        """
        path = args[0] if args else "simulation_state.json"
        self.system.save_state(path)
        print("State saved to %s" % path)

    def cmd_help(self, _args):
        """Print command help."""
        print(HELP_TEXT)

    def cmd_quit(self, _args):
        """Stop the main loop."""
        self.system.stop()


def configure_logging():
    """Configure logging from the SIM_LOG_LEVEL environment variable."""
    level_name = os.environ.get("SIM_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main(argv=None):
    """Program entry point.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        int: Process exit code.
    """
    configure_logging()
    args = list(sys.argv[1:] if argv is None else argv)
    config_path = args[0] if args else None
    try:
        system = init_system(config_path)
    except (OSError, ValueError) as exc:
        print("Failed to load configuration: %s" % exc)
        return 1
    globalvar.set_value("running", True)
    SimulatorApp(system).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
