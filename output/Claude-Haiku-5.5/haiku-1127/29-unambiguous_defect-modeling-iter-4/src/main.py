"""Command-line entry point for the Food Delivery Order Dispatch simulator.

Run with:  python src/main.py
"""

import logging
import sys

from display import DisplayManager
from input_manager import InputError, InputManager
from order import OrderManager
from path_planner import PathPlanner
from system import SystemManager, init_system

logger = logging.getLogger("dispatch.main")

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Place an order (restaurant then customer, 0-800).
                       Shows coordinates, assigned rider, and route map.
  tick [n]             Advance the simulation by n ticks (default 1).
  status               Show funds, tick, and every rider's state and orders.
  orders               Show details of all orders.
  riders               Show the event log of every rider.
  map                  Show the ASCII map with riders and active orders.
  save [file]          Save state to a JSON file (default dispatch_state.json).
  history              Show command history.
  help                 Show this help.
  quit / exit          Leave the program.
Shortcuts: s=start, t=tick, st=status, o=orders, r=riders, m=map, q=quit,
           !! repeats the last command, !n repeats history entry n.
"""


class DispatchApp:
    """Wires the managers together and runs the interactive command loop."""

    def __init__(self):
        """Initialize global state and all manager objects."""
        init_system()
        self.manager = SystemManager()
        self.order_manager = OrderManager()
        self.planner = PathPlanner()
        self.display = DisplayManager()
        self.inputs = InputManager()
        self.commands = {
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
        """Run the main loop until the system running flag is cleared."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.manager.is_running:
            try:
                line = self.inputs.read_line()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            except InputError as exc:
                print(f"Error: {exc}")
                continue
            if not line:
                continue
            name, args = self.inputs.parse_command(line)
            handler = self.commands.get(name)
            if handler is None:
                print(f"Unknown command '{name}'. Type 'help' for a list of commands.")
                continue
            try:
                handler(args)
            except InputError as exc:
                print(f"Error: {exc}")
            except Exception as exc:  # keep the simulator running after faults
                logger.exception("Command '%s' failed", name)
                print(f"Unexpected error: {exc}. System state has been preserved.")

    def active_orders(self):
        """Return orders not yet completed."""
        return self.order_manager.active_orders()

    def cmd_start(self, args):
        """Handle ``start``: create an order, assign a rider, and show the route."""
        if not args:
            args = self.inputs.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y: "
            ).replace(",", " ").split()
        coords = self.inputs.parse_coordinates(args)
        order = self.order_manager.create_order(coords)
        print(
            f"Order {order.id}: restaurant grid point {order.restaurant_pos}, "
            f"customer grid point {order.customer_pos}, distance {order.distance}"
        )

        rider = self.order_manager.dispatch(order)
        new_rider = False
        if rider is None:
            if not self.manager.can_recruit():
                self.order_manager.cancel(order)
                print(
                    f"No rider is available and funds ({self.manager.funds}) are below the "
                    f"recruitment cost ({self.manager.recruitment_cost}). Order rejected."
                )
                return
            rider = self.manager.recruit_rider()
            new_rider = True
            self.order_manager.assign(order, rider)

        queue_ahead = len(rider.orders) - 1
        route = self.planner.plan_route(rider.position, [order.restaurant_pos, order.customer_pos])
        distance = PathPlanner.path_length(route)
        ticks = PathPlanner.estimate_ticks(distance, rider.speed)

        print(f"New rider added: {'yes' if new_rider else 'no'}"
              + (f" (id {rider.rider_id}, funds now {self.manager.funds})" if new_rider else ""))
        print(f"Assigned rider: {rider.rider_id} (state: {rider.state_name})")
        print(f"Rider speed: {rider.speed} units/tick")
        print(f"Route distance: {distance} units, estimated time: {ticks} tick(s)")
        if queue_ahead > 0:
            print(f"Note: rider has {queue_ahead} order(s) ahead in queue.")
        print(self.display.render_map(self.manager.riders, self.active_orders(), route))

    def cmd_status(self, args):
        """Handle ``status``: print funds, tick, riders, and their orders."""
        print(self.display.render_status(
            self.manager.funds,
            self.manager.current_tick,
            self.manager.riders,
            self.order_manager_orders(),
        ))

    def order_manager_orders(self):
        """Return all orders, including completed ones."""
        from globalvar import get_value
        return get_value("orders", [])

    def cmd_orders(self, args):
        """Handle ``orders``: print details of every order."""
        print(self.display.render_orders(self.order_manager_orders()))

    def cmd_riders(self, args):
        """Handle ``riders``: print the status change log of every rider."""
        print(self.display.render_rider_logs(self.manager.riders))

    def cmd_map(self, args):
        """Handle ``map``: print the ASCII map of riders and active orders."""
        print(self.display.render_map(self.manager.riders, self.active_orders()))

    def cmd_tick(self, args):
        """Handle ``tick [n]``: advance the simulation."""
        steps = self.inputs.parse_int(args, 1, 1, 1000, "Tick count")
        before = len(self.order_manager.completed_orders())
        for _ in range(steps):
            self.manager.advance_tick()
        completed = len(self.order_manager.completed_orders()) - before
        print(f"Advanced {steps} tick(s). Current tick: {self.manager.current_tick}. "
              f"Orders completed: {completed}.")

    def cmd_save(self, args):
        """Handle ``save [file]``: persist state to JSON."""
        path = args[0] if args else "dispatch_state.json"
        try:
            self.manager.save_state(path)
        except OSError as exc:
            raise InputError(f"Could not write '{path}': {exc}") from None
        print(f"State saved to {path}.")

    def cmd_history(self, args):
        """Handle ``history``: list previously entered commands."""
        if not self.inputs.command_history:
            print("History is empty.")
            return
        for index, command in enumerate(self.inputs.command_history, start=1):
            print(f"{index:>4}  {command}")

    def cmd_help(self, args):
        """Handle ``help``: show the command list."""
        print(HELP_TEXT)

    def cmd_quit(self, args):
        """Handle ``quit``/``exit``: stop the main loop."""
        self.manager.is_running = False
        print("Goodbye.")


def main():
    """Configure logging and start the interactive simulator."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    app = DispatchApp()
    app.run()


if __name__ == "__main__":
    main()
