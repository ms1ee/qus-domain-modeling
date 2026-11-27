"""Command-line entry point for the food delivery dispatch simulator.

Run with:  python src/main.py [--debug]
"""

import argparse
import logging
import sys
from typing import Optional, Tuple

from display import DisplayManager
from globalvar import get_value
from grid import cell_index
from input_manager import COORDINATE_LABELS, Command, InputManager
from system import DEFAULT_STATE_PATH, init_system

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] [s]  Place an order. Without numbers you are prompted for
                           restaurant x/y and customer x/y (0-800 each).
  status              [st] Funds, rider count and every rider's state and orders.
  orders              [o]  Table of all orders with timing and assigned rider.
  riders              [r]  Full status-change log of every rider.
  map                 [m]  ASCII map with riders and active orders.
  tick [n]            [t]  Advance the simulation by n ticks (default 1).
  save [file]         [v]  Save configuration, riders and orders as JSON.
  history             [hi] Show the command history.
  help                [h]  Show this help.
  quit / exit         [q]  Leave the program.
History: '!!' repeats the last command, '!N' repeats history entry N."""


class App:
    """Interactive command loop tying together system, display and input."""

    def __init__(self) -> None:
        """Initialise the system and the user interface components."""
        init_system()
        self.system = get_value("system_manager")
        self.display = DisplayManager()
        self.inputs = InputManager()
        self.handlers = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "tick": self._cmd_tick,
            "save": self._cmd_save,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
        }

    def run(self) -> None:
        """Run the main loop until the user quits or input ends."""
        print("Food Delivery Order Dispatch System (8x8 grid, 800x800 units)")
        print("Type 'help' for commands. Funds: %d" % self.system.funds)
        while self.system.running and self.inputs.running:
            line = self.inputs.read_line("dispatch> ")
            if line is None:
                print()
                break
            if not line.strip():
                continue
            try:
                resolved = self.inputs.resolve_history(line)
                if resolved != line.strip():
                    print(f"Repeating: {resolved}")
                command = self.inputs.parse(resolved)
                self.handlers[command.name](command)
                self.inputs.record(resolved)
            except ValueError as exc:
                print(f"Error: {exc}")
            except Exception:  # keep the simulation alive on unexpected faults
                logger.exception("Unexpected error while executing a command")
                print("Unexpected internal error; system state was preserved. "
                      "Details were written to the log.")
        print("Goodbye.")

    # ------------------------------------------------------------------
    # coordinate prompting
    # ------------------------------------------------------------------
    def _prompt_coordinates(self) -> Optional[Tuple[int, int, int, int]]:
        """Interactively ask for the four coordinates.

        Returns:
            Tuple of (restaurant_x, restaurant_y, customer_x, customer_y), or
            None if the user cancelled or input ended.
        """
        values = []
        for label in COORDINATE_LABELS:
            while True:
                text = self.inputs.read_line(f"  {label} (0-800, 'cancel' to abort): ")
                if text is None or text.strip().lower() == "cancel":
                    return None
                try:
                    value = self.inputs.parse_int(text.strip(), label)
                    values.append(self.inputs.validate_coordinate(value, label))
                    break
                except ValueError as exc:
                    print(f"  Error: {exc}")
        return tuple(values)

    # ------------------------------------------------------------------
    # command handlers
    # ------------------------------------------------------------------
    def _cmd_start(self, command: Command) -> None:
        """Place an order and show the assignment and route."""
        if command.arguments:
            coords = tuple(command.arguments)
        else:
            coords = self._prompt_coordinates()
            if coords is None:
                print("Order entry cancelled.")
                return
        rx, ry, cx, cy = coords
        result = self.system.place_order((rx, ry), (cx, cy))
        order = result["order"]
        rider = result["rider"]
        route = result["route"]

        rgx, rgy = cell_index(rx, ry)
        cgx, cgy = cell_index(cx, cy)
        print(f"Order #{order.id} created at tick {order.start_time}.")
        print(f"  Restaurant: input ({rx},{ry}) -> grid cell ({rgx},{rgy}), "
              f"centre ({order.restaurant_x},{order.restaurant_y})")
        print(f"  Customer:   input ({cx},{cy}) -> grid cell ({cgx},{cgy}), "
              f"centre ({order.customer_x},{order.customer_y})")
        if result["new_riders"]:
            ids = ", ".join(str(i) for i in result["new_riders"])
            print(f"  New rider(s) added: {ids} (funds now {self.system.funds})")
        else:
            print(f"  No new rider added (funds {self.system.funds}, "
                  f"threshold {self.system.config.recruitment_threshold})")
        if rider is None:
            print("  No rider available. The order is queued and will be assigned "
                  "on the next tick.")
            return
        print(f"  Assigned to rider {rider.rider_id} at ({rider.x},{rider.y}); "
              f"speed {rider.speed} units/tick.")
        if route is None:
            print("  Route preview unavailable.")
            return
        print(self.display.render_map(riders=[rider], orders=[order], route=route))
        print(f"  Route: pickup then delivery, {route.total_distance} units, "
              f"about {route.estimated_ticks} ticks at speed {rider.speed}.")
        print(f"  Special approach (driveway): {'yes' if route.has_driveway else 'no'}")

    def _cmd_status(self, command: Command) -> None:
        """Show system funds and every rider's state and orders."""
        print(self.display.render_status(self.system))

    def _cmd_orders(self, command: Command) -> None:
        """Show all orders."""
        print(self.display.render_orders(self.system.order_manager.orders))

    def _cmd_riders(self, command: Command) -> None:
        """Show the status-change log of every rider."""
        print(self.display.render_rider_log(self.system.riders))

    def _cmd_map(self, command: Command) -> None:
        """Show the ASCII map with riders and active orders."""
        active = self.system.order_manager.active_orders()
        print(self.display.render_map(riders=self.system.riders, orders=active))

    def _cmd_tick(self, command: Command) -> None:
        """Advance the simulation."""
        count = command.arguments[0]
        for _ in range(count):
            self.system.tick()
        busy = sum(1 for r in self.system.riders if r.state != 0)
        print(f"Advanced {count} tick(s). Simulated time: {self.system.simulated_time}. "
              f"Riders: {len(self.system.riders)} (busy {busy}), "
              f"pending orders: {len(self.system.order_manager.pending)}.")

    def _cmd_save(self, command: Command) -> None:
        """Save the state to a JSON file."""
        parts = command.raw_input.split(maxsplit=1)
        path = parts[1].strip() if len(parts) > 1 else DEFAULT_STATE_PATH
        saved = self.system.save_state(path)
        print(f"State saved to {saved}")

    def _cmd_history(self, command: Command) -> None:
        """Show previously executed commands."""
        history = self.inputs.command_history
        if not history:
            print("No commands in history yet.")
            return
        for index, entry in enumerate(history, start=1):
            print(f"  {index:>4}  {entry}")

    def _cmd_help(self, command: Command) -> None:
        """Show the command reference."""
        print(HELP_TEXT)

    def _cmd_quit(self, command: Command) -> None:
        """Stop the program."""
        self.system.running = False
        self.inputs.running = False


def main(argv=None) -> int:
    """Program entry point.

    Args:
        argv: Optional list of command-line arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--debug", action="store_true",
                        help="enable debug logging to stderr")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    app = App()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
