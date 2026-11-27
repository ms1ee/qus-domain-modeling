"""Command-line entry point for the Food Delivery Order Dispatch System.

Run with: ``python src/main.py [--config config.json] [--save-state state.json]``
"""

import argparse
import logging
import sys

import globalvar
from display import DisplayManager
from input_manager import HELP_TEXT, InputManager
from order import OrderManager
from system import SystemManager, init_system, load_config

logger = logging.getLogger("dispatch")

MAX_RUN_TICKS = 10000


class DispatchApp:
    """Interactive command loop tying all modules together."""

    def __init__(self, config_path=None, state_path=None):
        """Initialise global state, managers and the command table.

        Args:
            config_path: Optional JSON configuration file.
            state_path: Optional JSON file to save state to on exit.
        """
        init_system(load_config(config_path))
        self.system = SystemManager()
        self.orders = OrderManager()
        self.display = DisplayManager()
        self.inputs = InputManager()
        self.state_path = state_path
        self.handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "run": self.cmd_run,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }
        # System starts with funds >= threshold, so one rider is recruited.
        self.system.check_recruitment()

    def run(self):
        """Run the read-evaluate-print loop until the system stops."""
        print("Food Delivery Order Dispatch System (8x8 grid, 800x800 units)")
        print("Type 'help' for commands.")
        while self.system.running:
            line = self.inputs.read_line("dispatch> ")
            if not line.strip():
                continue
            try:
                command_text = self.inputs.resolve(line)
                name, args = self.inputs.parse(command_text)
                if name is None:
                    print(f"Unknown command '{command_text.strip()}'. "
                          "Type 'help' for the command list.")
                    continue
                self.inputs.record(command_text.strip())
                self.handlers[name](args)
            except (ValueError, TypeError) as exc:
                print(f"Error: {exc}")
            except Exception:
                logger.exception("Unexpected error while running command")
                print("Unexpected internal error; system state preserved.")
        if self.state_path:
            self._save()
        print("Goodbye.")

    def cmd_start(self, args):
        """Create an order from four coordinates and assign a rider.

        Args:
            args: Optional four coordinate tokens. If omitted, prompts.
        """
        if args:
            tokens = args
        else:
            tokens = self.inputs.read_line(
                "Enter restaurant x y and customer x y (0-800): ")
        values = self.inputs.parse_coordinates(tokens)
        res_pos = (values[0], values[1])
        cus_pos = (values[2], values[3])

        added = self.system.check_recruitment()
        if not self.system.riders:
            print("No riders available and funds are insufficient to recruit.")
            return
        order = self.orders.create_order(res_pos, cus_pos)
        rider = self.orders.assign_order(order)
        if rider is None:
            print("Order could not be assigned to any rider.")
            return

        print(f"Order #{order.id} accepted at tick {order.start_time}.")
        print(f"Restaurant: input {order.raw_res_pos} -> cell centre "
              f"{order.res_pos}")
        print(f"Customer:   input {order.raw_cus_pos} -> cell centre "
              f"{order.cus_pos}")
        if added:
            print(f"New rider recruited: Rider #{self.system.riders[-1].rider_id}")
        else:
            print("No new rider recruited.")
        print(f"Assigned rider: #{rider.rider_id} "
              f"(state {rider.state_name}, {len(rider.orders)} order(s) "
              "queued including this one)")
        route = self.system_route(rider, order)
        print(self.display.render_route(rider, order, route))

    def system_route(self, rider, order):
        """Return the route waypoints from the rider through the order.

        Args:
            rider: Assigned rider.
            order: Order being planned.

        Returns:
            List of waypoints from the rider's position to the customer.
        """
        from path_planner import PathPlanner
        return PathPlanner().plan_route(rider.position, order.res_pos,
                                        order.cus_pos)

    def cmd_status(self, args):
        """Print funds, rider states and order lists."""
        print(self.display.status_text(
            self.system.riders, self.system.funds, self.system.tick,
            self.system.check_consistency()))

    def cmd_orders(self, args):
        """Print the table of all orders."""
        print(self.display.orders_text(self.orders.all_orders()))

    def cmd_riders(self, args):
        """Print the status-change log of every rider."""
        print(self.display.riders_text(self.system.riders))

    def cmd_map(self, args):
        """Print the ASCII map with riders and active orders."""
        print(self.display.render_map(self.system.riders,
                                      self.orders.active_orders()))

    def cmd_tick(self, args):
        """Advance simulated time by the requested number of ticks.

        Args:
            args: Optional tick count (1-1000, default 1).
        """
        count = self.inputs.parse_count(args)
        for _ in range(count):
            self._step_and_report()
        print(f"Current tick: {self.system.tick}. Active orders: "
              f"{len(self.orders.active_orders())}. Funds: {self.system.funds}.")

    def cmd_run(self, args):
        """Advance time until every active order has been delivered."""
        steps = 0
        while self.orders.active_orders() and steps < MAX_RUN_TICKS:
            self._step_and_report()
            steps += 1
        if self.orders.active_orders():
            print(f"Stopped after {MAX_RUN_TICKS} ticks with orders still "
                  "active.")
        elif steps == 0:
            print("No active orders.")
        else:
            print(f"All orders delivered after {steps} tick(s). "
                  f"Current tick: {self.system.tick}.")

    def cmd_history(self, args):
        """Print the numbered command history."""
        print(self.display.history_text(self.inputs.history))

    def cmd_help(self, args):
        """Print the command help text."""
        print(HELP_TEXT)

    def cmd_quit(self, args):
        """Stop the main loop."""
        self.system.stop()
        print("Stopping simulation.")

    def _step_and_report(self):
        """Advance one tick and print orders completed during that tick."""
        before = {o.id for o in self.orders.all_orders()
                  if o.status == "completed"}
        self.system.advance_tick()
        for order in self.orders.all_orders():
            if order.status == "completed" and order.id not in before:
                print(f"  tick {order.completion_time}: order #{order.id} "
                      f"delivered by rider #{order.rider_id} "
                      f"(time taken {order.time_taken} ticks, distance "
                      f"{order.distance})")

    def _save(self):
        """Persist the current state to the configured file."""
        try:
            self.system.save_state(self.state_path)
            print(f"State saved to {self.state_path}.")
        except OSError as exc:
            print(f"Error: could not save state: {exc}")


def main(argv=None):
    """Parse command-line options and start the dispatch shell.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Food delivery order dispatch simulator")
    parser.add_argument("--config", default=None,
                        help="JSON file with system parameters")
    parser.add_argument("--save-state", default=None,
                        help="JSON file to write the final state to on exit")
    parser.add_argument("--debug", action="store_true",
                        help="enable debug logging to stderr")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr)

    app = DispatchApp(config_path=args.config, state_path=args.save_state)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
