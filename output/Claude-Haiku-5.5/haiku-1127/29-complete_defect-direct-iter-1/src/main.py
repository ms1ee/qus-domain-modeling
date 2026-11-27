"""Command-line entry point for the food delivery dispatch simulator.

Run with ``python src/main.py`` (optionally ``--config path/to/config.json``).
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa: E402
import globalvar  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402
from order import OrderManager  # noqa: E402
from path_planner import PathPlanner  # noqa: E402
from persistence import load_configuration, save_snapshot  # noqa: E402
from system import SystemManager, init_system  # noqa: E402

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant then customer, 0-800) and dispatch it
  status               System funds and rider states
  orders               All orders with time, distance and rider
  riders               Status-change log for every rider
  map                  8x8 cell map and street map of current positions
  tick [n]             Advance the simulation by n ticks (default 1)
  save [path]          Save a JSON snapshot of the system state
  history              Show command history
  help                 Show this help
  quit / exit          Leave the program
Shortcuts: s=start st=status o=orders r=riders m=map t=tick v=save h=history
           q=quit  ?=help  !!=repeat last command  !n=repeat command n
"""


class DispatchApp:
    """Connects user commands to the simulation components."""

    def __init__(self):
        """Create the application components on top of the global state."""
        self.system = SystemManager()
        self.orders = OrderManager()
        self.display = DisplayManager()
        self.inputs = InputManager()
        self.handlers = {
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

    def run(self):
        """Run the interactive command loop until quit or end of input."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while globalvar.get_value("running", True):
            try:
                line = self.inputs.read_line()
                if not line:
                    continue
                command, args = self.inputs.parse(line)
                self.handlers[command](args)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except ValueError as exc:
                print(f"Input error: {exc}")
            except Exception as exc:  # Graceful recovery for unexpected faults.
                logger.exception("Unexpected error while processing command")
                print(f"Internal error: {exc}. Attempting state recovery.")
                self.recover_state()
        print("Goodbye.")

    def recover_state(self):
        """Repair common inconsistencies after an unexpected error."""
        if not isinstance(globalvar.get_value("funds", 0), int):
            globalvar.set_value("funds", 0)
        riders = globalvar.get_value("riders", []) or []
        for rider in riders:
            if not rider.orders and rider.state != config.STATE_IDLE:
                rider.state = config.STATE_IDLE
                rider.path = []
                rider.target = None

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def cmd_start(self, args):
        """Create an order, dispatch it and simulate until it is delivered."""
        if args:
            coords = self.inputs.parse_coordinates(args)
        else:
            coords = self.inputs.prompt_coordinates()

        order = self.orders.create_order(coords)
        rider = self.orders.try_assign(order)
        rider_added = False
        if rider is None:
            new_rider = self.system.check_recruitment()
            if new_rider is not None:
                rider_added = True
                rider = self.orders.try_assign(order)
        if rider is None:
            self.orders.enqueue(order)

        estimate = None
        if rider is not None:
            estimate = PathPlanner.estimate_ticks(
                rider.position, [order.res_grid, order.cus_grid], rider.speed)
        print(self.display.format_start_summary(order, rider, rider_added, estimate))

        ticks = 0
        while order.status != "completed" and ticks < config.MAX_SIM_TICKS:
            self.system.tick()
            ticks += 1

        if order.status == "completed":
            print(f"Order #{order.id} delivered by rider #{order.rider_id} "
                  f"after {order.time_taken} tick(s); "
                  f"distance {order.distance} units.")
        else:
            print(f"Order #{order.id} not delivered within "
                  f"{config.MAX_SIM_TICKS} ticks (status: {order.status}).")

        riders = self.system.riders()
        print(self.display.render_route(order, riders=riders))

    def cmd_status(self, _args):
        """Print the system fund balance and every rider's state."""
        print(self.display.format_status(self.system.funds(), self.system.riders()))

    def cmd_orders(self, _args):
        """Print the details of all orders."""
        print(self.display.format_orders(self.orders.all_orders()))

    def cmd_riders(self, _args):
        """Print the status-change history of all riders."""
        print(self.display.format_riders_log(self.system.riders()))

    def cmd_map(self, _args):
        """Print the cell map and the street map of current positions."""
        riders = self.system.riders()
        orders = self.orders.all_orders()
        print(self.display.render_cell_map(riders, orders))
        print()
        print(self.display.render_street_map(riders, orders, []))

    def cmd_tick(self, args):
        """Advance the simulation by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError as exc:
                raise ValueError("tick count must be an integer.") from exc
        if not 1 <= count <= config.MAX_SIM_TICKS:
            raise ValueError(f"tick count must be between 1 and {config.MAX_SIM_TICKS}.")
        for _ in range(count):
            self.system.tick()
        print(f"Advanced {count} tick(s); now at tick "
              f"{globalvar.get_value('tick', 0)}. Funds: {self.system.funds()}.")

    def cmd_save(self, args):
        """Save a JSON snapshot of the system state."""
        path = args[0] if args else None
        try:
            written = save_snapshot(path)
        except OSError as exc:
            raise ValueError(f"Could not save snapshot: {exc}") from exc
        print(f"Snapshot saved to {written}.")

    def cmd_history(self, _args):
        """Print the command history."""
        if not self.inputs.history:
            print("History is empty.")
            return
        for index, entry in enumerate(self.inputs.history, start=1):
            print(f"  {index:>3}  {entry}")

    def cmd_help(self, _args):
        """Print the command help text."""
        print(HELP_TEXT)

    def cmd_quit(self, _args):
        """Stop the main loop."""
        globalvar.set_value("running", False)


def _configure_logging():
    """Send log output to the log file so the console stays clean."""
    logging.basicConfig(
        filename=config.LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv=None):
    """Program entry point.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        int: Process exit status.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    _configure_logging()

    if "--config" in argv:
        index = argv.index("--config")
        if index + 1 >= len(argv):
            print("Usage: main.py [--config CONFIG_FILE]")
            return 2
        try:
            applied = load_configuration(argv[index + 1])
            print(f"Loaded parameters: {', '.join(applied) if applied else 'none'}")
        except (OSError, ValueError) as exc:
            print(f"Configuration error: {exc}")
            return 1

    init_system()
    DispatchApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
