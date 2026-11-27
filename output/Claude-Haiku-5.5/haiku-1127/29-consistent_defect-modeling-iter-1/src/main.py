"""Command-line entry point for the food delivery dispatch simulator."""

import logging
import math
import os
import sys
from typing import Callable, Dict, List, Optional

from display import DisplayManager
from globalvar import get_value
from input_manager import InputError, InputManager
from order_model import Order
from path_planner import PathPlanner
from rider import Rider
from system import SystemManager, init_system, load_config

LOG_FILE = "dispatch.log"
CONFIG_FILE = "config.json"
STATE_FILE = "dispatch_state.json"
MAX_RUN_TICKS = 10000

HELP_TEXT = """Commands:
  start  (s)  [rx ry cx cy]  Place an order (restaurant then customer, 0-1000)
  status (st)                Funds, riders and their orders
  orders (o)                 All orders with timing and assignment
  riders (r)                 Status-change log for every rider
  map    (m)                 ASCII map of riders and orders
  tick   (t)  [n]            Advance simulated time by n ticks (default 1)
  run                        Advance until all orders are completed
  save                       Save state to dispatch_state.json
  help   (h, ?)              Show this help
  quit   (q, exit)           Exit the program
  !!                         Repeat the previous command"""


class Simulator:
    """Interactive session tying together system, display and input modules."""

    def __init__(self) -> None:
        init_system()
        if os.path.exists(CONFIG_FILE):
            try:
                load_config(CONFIG_FILE)
            except (OSError, ValueError) as exc:
                print(f"Warning: could not load {CONFIG_FILE}: {exc}. Using defaults.")
        self.system = SystemManager()
        self.inputs = InputManager()
        self.display = DisplayManager()
        self.planner = PathPlanner()
        self._commands: Dict[str, Callable[[List[str]], None]] = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "run": self.cmd_run,
            "save": self.cmd_save,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }
        self._enable_line_editing()

    @staticmethod
    def _enable_line_editing() -> None:
        """Enable arrow-key history on platforms where readline exists."""
        try:
            import readline  # noqa: F401  (side effect: line editing)
        except ImportError:
            pass

    def run(self) -> int:
        """Run the interactive loop until quit or end of input."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.running:
            try:
                raw = input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            try:
                self.execute(raw)
            except InputError as exc:
                print(f"Error: {exc}")
            except Exception:  # keep the session alive on unexpected errors
                logging.getLogger(__name__).exception("Unexpected error while executing command")
                print("Error: unexpected failure; system state has been preserved.")
        return 0

    def execute(self, raw: str) -> None:
        """Parse and dispatch one command line."""
        if not raw.strip():
            return
        name, args, text = self.inputs.resolve(raw)
        self._commands[name](args)
        self.inputs.record(text)

    # ------------------------------------------------------------------ #
    # Command handlers
    # ------------------------------------------------------------------ #
    def cmd_start(self, args: List[str]) -> None:
        """Create an order, dispatch it and show the planned route."""
        if not args:
            args = input("Enter restaurant_x restaurant_y customer_x customer_y: ").split()
        values = self.inputs.parse_coordinates(args)
        order = self.system.order_manager.create_order(values, self.system.simulated_time)
        rider, recruited = self.system.dispatch_order(order)

        print(f"Restaurant grid location: {order.res_pos}")
        print(f"Customer grid location:   {order.cus_pos}")
        if recruited:
            print(f"New rider added: yes (funds now {self.system.funds})")
        else:
            print("New rider added: no")

        if rider is None:
            print(
                f"No rider available (funds {self.system.funds}). Order {order.id} "
                "is pending and will be retried on each tick."
            )
            return

        stops = [order.res_pos, order.cus_pos]
        occupied = [r.position for r in self.system.riders if r is not rider]
        waypoints = self.planner.plan_route(rider.position, stops, occupied)
        total = self.planner.path_length(rider.position, waypoints)
        ticks = math.ceil(total / rider.speed) if rider.speed else 0
        print(f"Assigned to rider R{rider.rider_id} (order {order.id}).")
        if len(rider.active_orders()) > 1:
            print("Note: rider already has active orders; this order is queued.")
        print(f"Speed: {rider.speed} units/tick  Route length: {total} units  "
              f"Estimated time: {ticks} ticks")
        route = [rider.position] + waypoints
        print(self.display.render_map(self.system.riders, [order], routes=[route]))

    def cmd_status(self, args: List[str]) -> None:
        """Print funds and the state of every rider."""
        print(self.display.render_status(self.system.funds, self.system.riders))
        for rider in self.system.riders:
            for order in rider.orders:
                print(f"    R{rider.rider_id} order {order.id}: {order.status}")

    def cmd_orders(self, args: List[str]) -> None:
        """Print all orders."""
        print(self.display.render_orders(self.system.order_manager.orders()))

    def cmd_riders(self, args: List[str]) -> None:
        """Print the status-change log of every rider."""
        print(self.display.render_rider_logs(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map of riders and active orders."""
        orders: List[Order] = self.system.order_manager.orders()
        routes = []
        for rider in self.system.riders:
            current = rider.current_order()
            if current is not None:
                target = current.res_pos if rider.state == 1 else current.cus_pos
                routes.append([rider.position, target])
        print(self.display.render_map(self.system.riders, orders, routes=routes))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance simulated time by one or more ticks."""
        count = self.inputs.parse_count(args, default=1)
        self._advance(count)
        print(f"Simulated time: {self.system.simulated_time}")

    def cmd_run(self, args: List[str]) -> None:
        """Advance time until every order is completed (bounded)."""
        ticks = 0
        while ticks < MAX_RUN_TICKS and any(
            o.status != "completed" for o in self.system.order_manager.orders()
        ):
            self._advance(1)
            ticks += 1
        print(f"Simulated time: {self.system.simulated_time} (ran {ticks} ticks)")

    def cmd_save(self, args: List[str]) -> None:
        """Persist the state to a JSON file."""
        self.system.save_state(STATE_FILE)
        print(f"State saved to {STATE_FILE}")

    def cmd_help(self, args: List[str]) -> None:
        """Print the command reference."""
        print(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Terminate the session."""
        self.system.stop()
        print("Goodbye.")

    def _advance(self, ticks: int) -> None:
        """Run ticks and print any new rider events."""
        for _ in range(ticks):
            before = {r.rider_id: len(r.log) for r in self.system.riders}
            self.system.tick()
            for rider in self.system.riders:
                for entry in rider.log[before.get(rider.rider_id, 0):]:
                    if entry["event"] == "spawn":
                        continue
                    order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                    print(
                        f"  t={entry['time']} R{rider.rider_id} "
                        f"{entry['event'].replace('_', ' ')} order={order}"
                    )


def main() -> int:
    """Configure logging and start the interactive simulator."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    simulator = Simulator()
    return simulator.run()


if __name__ == "__main__":
    sys.exit(main())
