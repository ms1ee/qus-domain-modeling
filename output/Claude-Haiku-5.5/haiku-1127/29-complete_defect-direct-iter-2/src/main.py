"""Command-line entry point for the food delivery dispatch simulator.

Run with ``python src/main.py``. Commands: start, status, orders, riders,
map, tick, save, history, help, quit (see ``help`` for details).
"""

import argparse
import logging
import sys

import config
import globalvar
import system
from config import DEFAULT_CONFIG_PATH, DEFAULT_STATE_PATH, MAX_TICKS_PER_COMMAND
from display import DisplayManager
from input_manager import InputManager
from order_model import STATUS_COMPLETED
from path_planner import PathPlanner, estimate_ticks, path_length

logger = logging.getLogger("dispatch")

BANNER = ("Food Delivery Dispatch Simulator\n"
          "Type 'help' for commands, 'quit' to exit.")

HELP_TEXT = """Commands:
  start [rx ry cx cy]   Place an order. rx/ry = restaurant, cx/cy = customer
                        (integers 0-800). Prompts if values are omitted.
  status (st)           System funds, rider count, and each rider's state.
  orders (o)            Details for every order.
  riders (r)            Status-change log for every rider.
  map (m)               ASCII map of riders and active orders.
  tick [n] (t)          Advance the simulation by n ticks (default 1).
  save [file] (none)    Save a JSON snapshot (default dispatch_state.json).
  history (hist)        Show command history.
                        '!!' repeats the last command, '!n' repeats entry n.
  help (h, ?)           Show this help.
  quit (q, exit)        Exit the program."""


class DispatchApp:
    """Ties the system, display and input managers into a command loop.

    Attributes:
        manager: The SystemManager instance.
        display: The DisplayManager instance.
        inp: The InputManager instance.
        planner: The PathPlanner instance.
        state_file: Default destination for the save command.
    """

    def __init__(self, state_file=DEFAULT_STATE_PATH):
        """Initialise the system and the command handlers.

        Args:
            state_file: Default path used by the save command.
        """
        self.manager = system.init_system()
        self.display = DisplayManager()
        self.inp = InputManager()
        self.planner = PathPlanner()
        self.state_file = state_file
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
        }

    def run(self):
        """Run the interactive command loop until quit or end of input."""
        print(BANNER)
        while globalvar.get_value("running"):
            try:
                line = self.inp.read_line()
                if not line:
                    continue
                command, args = self.inp.parse(line)
                self.handlers[command](args)
            except ValueError as exc:
                print(f"Error: {exc}")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            except Exception:  # pylint: disable=broad-except
                logger.exception("Unexpected failure in command loop")
                print("An internal error occurred. Recovering system state.")
                self._recover()
        print("Goodbye.")

    def _recover(self):
        """Run consistency checks and repair the system state."""
        issues = self.manager.recover()
        for issue in issues:
            print(f"Recovered: {issue}")

    def cmd_start(self, args):
        """Place an order, assign a rider and show the route map.

        Args:
            args: Optional four coordinate tokens.
        """
        if args:
            values = self.inp.parse_coordinates(args)
        else:
            values = self.inp.prompt_coordinates()
        restaurant = (values[0], values[1])
        customer = (values[2], values[3])

        order, new_rider = self.manager.submit_order(restaurant, customer)
        print(f"Restaurant grid center: {order.res_pos}")
        print(f"Customer grid center: {order.cus_pos}")
        if new_rider is not None:
            print(f"New rider added: yes (rider #{new_rider.rider_id})")
        else:
            print("New rider added: no")
        print(f"Order #{order.id} street distance: {order.distance} units")

        if order.rider_id is None:
            print("No rider available yet; the order is queued as pending.")
            return

        rider = self.manager.get_rider(order.rider_id)
        route = self.planner.plan_route(rider.position,
                                        [order.res_pos, order.cus_pos])
        length = path_length(rider.position, route)
        ticks = estimate_ticks(length, rider.speed)
        queued = len(rider.orders) - 1
        print(self.display.render_route_summary(rider, order, length, ticks,
                                                queued))
        points = [rider.position] + route
        print(self.display.render_map(riders=[rider], orders=[order],
                                      route=points))

    def cmd_status(self, _args):
        """Print the system status snapshot.

        Args:
            _args: Unused.
        """
        print(self.display.render_status(
            self.manager.funds, self.manager.tick, self.manager.riders,
            len(self.manager.order_manager.pending_orders())))

    def cmd_orders(self, _args):
        """Print the table of all orders.

        Args:
            _args: Unused.
        """
        print(self.display.render_orders(self.manager.order_manager
                                         .all_orders()))

    def cmd_riders(self, _args):
        """Print the status-change records of all riders.

        Args:
            _args: Unused.
        """
        print(self.display.render_rider_logs(self.manager.riders))

    def cmd_map(self, _args):
        """Print the ASCII map with riders and active orders.

        Args:
            _args: Unused.
        """
        active = [o for o in self.manager.order_manager.active_orders
                  if o.status != STATUS_COMPLETED]
        print(self.display.render_map(riders=self.manager.riders,
                                      orders=active))

    def cmd_tick(self, args):
        """Advance the simulation.

        Args:
            args: Optional tick count.

        Raises:
            ValueError: If the count is not a valid integer in range.
        """
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"tick count must be an integer, "
                                 f"got '{args[0]}'") from None
        if not 1 <= count <= MAX_TICKS_PER_COMMAND:
            raise ValueError(f"tick count must be between 1 and "
                             f"{MAX_TICKS_PER_COMMAND}")
        completed = self.manager.advance(count)
        print(f"Advanced {count} tick(s); now at tick {self.manager.tick}.")
        if completed:
            print(f"Completed order(s): {', '.join(str(i) for i in completed)}")
        print(f"Funds: {self.manager.funds}; riders: "
              f"{len(self.manager.riders)}")

    def cmd_save(self, args):
        """Save the current state to a JSON file.

        Args:
            args: Optional file path.
        """
        path = args[0] if args else self.state_file
        try:
            self.manager.save_state(path)
            print(f"State saved to {path}")
        except OSError as exc:
            print(f"Error: could not save state: {exc}")

    def cmd_history(self, _args):
        """Print the command history.

        Args:
            _args: Unused.
        """
        if not self.inp.history:
            print("History is empty.")
            return
        for index, line in enumerate(self.inp.history, start=1):
            print(f"{index:>4}  {line}")

    def cmd_help(self, _args):
        """Print the help text.

        Args:
            _args: Unused.
        """
        print(HELP_TEXT)

    def cmd_quit(self, _args):
        """Stop the main loop.

        Args:
            _args: Unused.
        """
        globalvar.set_value("running", False)


def main(argv=None):
    """Parse arguments, load configuration and run the application.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Food delivery order dispatch simulator.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH,
                        help="JSON file with system parameters")
    parser.add_argument("--state-file", default=DEFAULT_STATE_PATH,
                        help="default file for the save command")
    parser.add_argument("--log-file", default=None,
                        help="write log output to this file")
    parser.add_argument("--debug", action="store_true",
                        help="enable debug logging")
    args = parser.parse_args(argv)

    handlers = []
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file, encoding="utf-8"))
    else:
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers)

    config.load_config(args.config)
    app = DispatchApp(state_file=args.state_file)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
