"""Command-line entry point for the food delivery dispatch simulator.

Usage:
    python src/main.py [--config CONFIG_FILE] [--debug]

Each ``tick`` command advances simulated time by one unit (or N units when
given an argument). Type ``help`` inside the program for the command list.
"""

import argparse
import logging
import sys

import globalvar
from display import DisplayManager
from input_manager import CommandError, InputManager
from path_planner import PathPlanner
from system import init_system

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant then customer, 0-1000) and dispatch it
  status               Show funds, riders and their states
  orders               Show all orders with timing and assignment details
  riders               Show every rider status change log entry
  map                  Show the ASCII map with riders and active orders
  tick [n]             Advance simulated time by n ticks (default 1)
  save [file]          Save system state to a JSON file (default dispatch_state.json)
  history              Show command history
  help                 Show this help
  quit / exit          Leave the program
Shortcuts: s, st, o, r, m, t, w, h, ?, q, e, !! (repeat last), !n (repeat entry n)"""


class Application:
    """Interactive session tying together system, display and input handling.

    Attributes:
        system (SystemManager): Core simulation manager.
        display (DisplayManager): Rendering helper.
        inputs (InputManager): Command parser and history.
        planner (PathPlanner): Route planner used for route previews.
    """

    def __init__(self, config_path=None):
        """Initialise the system and register the command handlers.

        Args:
            config_path: Optional JSON configuration file.
        """
        self.system = init_system(config_path)
        self.display = DisplayManager()
        self.inputs = InputManager()
        self.planner = PathPlanner()
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
        """Run the main interaction loop until the system stops."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.stop()
                break
            self.handle_line(line)
        print("Goodbye.")

    def handle_line(self, line):
        """Parse and execute one command line, recovering from any error.

        Args:
            line: Raw input text.
        """
        try:
            command, args = self.inputs.parse_line(line)
            if command is None:
                return
            self.handlers[command](args)
        except CommandError as exc:
            print(f"Error: {exc}")
        except ValueError as exc:
            print(f"Invalid input: {exc}")
        except Exception as exc:  # Error recovery: keep the session alive.
            logger.exception("Unexpected error while handling command")
            print(f"Unexpected error: {exc}. System state has been preserved.")

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def cmd_start(self, args):
        """Create and dispatch an order, showing the route on the map."""
        if not args:
            args = input("Enter restaurant_x restaurant_y customer_x customer_y: ").split()
        values = self.inputs.parse_coordinates(args)
        result = self.system.submit_order(values[:2], values[2:])
        order = result["order"]
        rider = result["rider"]
        new_rider = result["new_rider"]

        print(f"Order #{order.id} created at tick {order.start_time}")
        print(f"Restaurant grid point: ({order.res_pos[0]}, {order.res_pos[1]})")
        print(f"Customer grid point:   ({order.cus_pos[0]}, {order.cus_pos[1]})")
        if new_rider is not None:
            print(f"New rider added: yes (Rider #{new_rider.rider_id}); "
                  f"funds now {self.system.funds}")
        else:
            print("New rider added: no")

        if rider is None:
            print("No rider available. The order stays pending and will be retried each tick.")
            return

        print(f"Assigned to Rider #{rider.rider_id} (status: {rider.state_name}, "
              f"active orders: {len(rider.active_orders())})")
        route = self.planner.plan_route(rider.position, order.res_pos)
        leg = self.planner.plan_route(order.res_pos, order.cus_pos)
        full_route = route + leg[1:]
        distance = self.planner.route_length(full_route)
        ticks = self.planner.estimate_ticks(distance, rider.speed)
        print(f"Speed: {rider.speed} units/tick; route length: {distance} units; "
              f"estimated time: {ticks} ticks")
        print(self.display.render_map(riders=[rider], orders=[order], route=full_route))

    def cmd_status(self, args):
        """Print the system status snapshot."""
        print(self.display.render_status(self.system))

    def cmd_orders(self, args):
        """Print the details of all orders."""
        print(self.display.render_orders(self.system.order_manager.orders))

    def cmd_riders(self, args):
        """Print the status-change history of every rider."""
        print(self.display.render_rider_logs(self.system.riders))

    def cmd_map(self, args):
        """Print the ASCII map with riders and active orders."""
        active = [o for o in self.system.order_manager.orders if o.status != "completed"]
        print(self.display.render_map(riders=self.system.riders, orders=active))

    def cmd_tick(self, args):
        """Advance the simulation and print the events that occurred."""
        steps = 1
        if args:
            try:
                steps = int(args[0])
            except ValueError:
                raise CommandError(f"'{args[0]}' is not an integer.") from None
            if not 1 <= steps <= 10000:
                raise CommandError("Tick count must be between 1 and 10000.")
        for _ in range(steps):
            before = {rider.rider_id: len(rider.log) for rider in self.system.riders}
            self.system.tick()
            for rider in self.system.riders:
                for entry in rider.log[before.get(rider.rider_id, 0):]:
                    print(self.display.format_log_entry(rider, entry))
        print(f"Now at tick {self.system.current_tick}; funds {self.system.funds}; "
              f"riders {len(self.system.riders)}")

    def cmd_save(self, args):
        """Save the system state to a JSON file."""
        path = args[0] if args else "dispatch_state.json"
        self.system.save_state(path)
        print(f"State saved to {path}")

    def cmd_history(self, args):
        """Print the command history."""
        if not self.inputs.command_history:
            print("No commands yet.")
            return
        for index, entry in enumerate(self.inputs.command_history, start=1):
            print(f"{index:>4}  {entry}")

    def cmd_help(self, args):
        """Print the help text."""
        print(HELP_TEXT)

    def cmd_quit(self, args):
        """Stop the main loop."""
        self.system.stop()


def main(argv=None):
    """Parse arguments, configure logging and run the application.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None, help="Path to a JSON config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    options = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if options.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = Application(config_path=options.config)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
