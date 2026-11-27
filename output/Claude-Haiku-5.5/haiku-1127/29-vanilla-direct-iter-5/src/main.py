"""Command-line entry point for the Food Delivery Order Dispatch simulator.

Run with::

    python src/main.py [--config PATH] [--debug]
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Callable, Dict, List, Optional

import globalvar
from display import DisplayManager
from input_manager import InputManager
from order_model import Order
from path_planner import PathPlanner
from system import SystemManager, init_system

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant then customer, 0-800).
                       Shortcut: s. Prompts if no coordinates are given.
  status               System funds, riders and their orders.       (st)
  orders               All orders: start, locations, distance, time. (o)
  riders               Every rider status change log.                (r)
  map                  ASCII map with riders and active orders.      (m)
  tick [n]             Advance the simulation by n ticks (default 1). (t)
  run                  Advance until all orders are completed.        (u)
  history              Show command history.                         (hist)
  !!                   Repeat the last command.
  help                 Show this help.                               (h, ?)
  quit / exit          Save state and exit.                          (q)
"""


class DispatchApp:
    """Interactive application that dispatches commands to the core modules."""

    def __init__(self, reader: Callable[[str], str] = input,
                 output: Callable[..., None] = print) -> None:
        """Create the application.

        Args:
            reader: Line reader (``input`` by default; injectable for tests).
            output: Output function (``print`` by default).
        """
        self.inputs = InputManager(reader)
        self.display = DisplayManager()
        self.out = output
        self.sm: Optional[SystemManager] = None
        self.commands: Dict[str, Callable[[List[str]], None]] = {
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

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self, config_path: Optional[str] = None) -> None:
        """Initialise the system and print the welcome banner."""
        init_system(config_path)
        self.sm = SystemManager()
        self.out("Food Delivery Order Dispatch System")
        self.out(f"Funds: {self.sm.funds} | Map: 800x800 (8x8 cells) | Type 'help'.")

    def loop(self) -> None:
        """Run the read-evaluate loop until the system stops running."""
        while globalvar.get_value("system_running", False):
            try:
                line = self.inputs.read_line()
            except EOFError:
                self.out("")
                break
            except KeyboardInterrupt:
                self.out("")
                break
            if not line:
                continue
            if line == "!!":
                last = self.inputs.last_command()
                if last is None:
                    self.out("No previous command to repeat.")
                    continue
                self.out(f"Repeating: {last}")
                line = last
            self.inputs.record(line)
            command, args = self.inputs.parse(line)
            handler = self.commands.get(command)
            if handler is None:
                self.out(f"Unknown command '{command}'. Type 'help' for the command list.")
                continue
            try:
                handler(args)
            except ValueError as exc:
                self.out(f"Input error: {exc}")
            except RuntimeError as exc:
                self.out(f"Error: {exc}")
            except Exception:  # keep the session alive on unexpected errors
                logger.exception("Unexpected error while running '%s'", command)
                self.out("Unexpected internal error; system state has been preserved.")
            self._check_consistency()

    def shutdown(self) -> None:
        """Save state to disk and stop the main loop."""
        if self.sm is not None:
            try:
                path = self.sm.save_state()
                self.out(f"State saved to {path}")
            except OSError as exc:
                logger.error("Could not save state: %s", exc)
                self.out(f"Could not save state: {exc}")
        globalvar.set_value("system_running", False)
        self.out("Goodbye.")

    def _check_consistency(self) -> None:
        """Log any internal consistency problems."""
        if self.sm is None:
            return
        for problem in self.sm.check_consistency():
            logger.warning("Consistency check: %s", problem)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _cell_label(point) -> str:
        """Return the ``(column,row)`` grid cell label for a centre point."""
        col, row = PathPlanner.cell_of(point[0], point[1])
        return f"({col},{row})"

    def _require_system(self) -> SystemManager:
        """Return the system manager or raise if not initialised."""
        if self.sm is None:
            raise RuntimeError("system is not initialised")
        return self.sm

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #
    def cmd_start(self, args: List[str]) -> None:
        """Create and dispatch an order from four coordinates."""
        sm = self._require_system()
        coords = InputManager.parse_coordinates(args) if args else self.inputs.prompt_coordinates()
        result = sm.submit_order(coords)
        order: Order = result["order"]
        rider = result["rider"]

        self.out(f"Order #{order.id} created at tick {order.start_tick}.")
        self.out(f"  Restaurant: input {order.raw_res_pos} -> grid cell "
                 f"{self._cell_label(order.res_pos)}, centre {order.res_pos}")
        self.out(f"  Customer:   input {order.raw_cus_pos} -> grid cell "
                 f"{self._cell_label(order.cus_pos)}, centre {order.cus_pos}")
        self.out(f"  Straight-line distance: {order.distance} units")
        for new_rider in result["new_riders"]:
            self.out(f"  New rider added: #{new_rider.rider_id} at {new_rider.position} "
                     f"(system funds now {sm.funds})")
        if rider is None:
            self.out("  No rider available: order remains pending (insufficient funds to recruit).")
            return

        self.out(f"  Assigned to rider #{rider.rider_id} "
                 f"(distance to restaurant {result['distance']:.1f} units).")
        route = result["route"]
        if route:
            self.out(f"  Speed: {rider.speed} units/tick | Estimated time: {result['eta']} ticks")
            self.out(self.display.render_map(sm.riders, [order], route=route))
        else:
            queued = max(0, len(rider.orders) - 1)
            self.out(f"  Rider #{rider.rider_id} is busy with {queued} earlier order(s); "
                     "the route starts when the rider is free. Use 'map' to follow progress.")

    def cmd_status(self, args: List[str]) -> None:
        """Print the system snapshot."""
        sm = self._require_system()
        self.out(self.display.render_status(sm.funds, sm.riders))
        self.out(f"Clock tick: {sm.tick_count} | Active orders: {len(sm.riders and [o for r in sm.riders for o in r.orders]) if sm.riders else 0}")

    def cmd_orders(self, args: List[str]) -> None:
        """Print every order's details."""
        from order import OrderManager  # local import keeps module graph simple
        self._require_system()
        self.out(self.display.render_orders(OrderManager.all_orders()))

    def cmd_riders(self, args: List[str]) -> None:
        """Print every rider's status change log."""
        sm = self._require_system()
        self.out(self.display.render_rider_logs(sm.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map with riders and active orders."""
        from order import OrderManager
        sm = self._require_system()
        self.out(self.display.render_map(sm.riders, OrderManager.active_orders()))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the clock by one or more ticks."""
        sm = self._require_system()
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError as exc:
                raise ValueError("tick count must be an integer") from exc
        if not 1 <= count <= 10000:
            raise ValueError("tick count must be between 1 and 10000")
        for _ in range(count):
            sm.tick()
        from order import OrderManager
        self.out(f"Advanced {count} tick(s). Clock: {sm.tick_count} | "
                 f"Active orders: {len(OrderManager.active_orders())}")

    def cmd_run(self, args: List[str]) -> None:
        """Advance until every order has been completed."""
        sm = self._require_system()
        elapsed = sm.run_until_idle()
        self.out(f"All orders completed after {elapsed} tick(s). Clock: {sm.tick_count}.")

    def cmd_history(self, args: List[str]) -> None:
        """Print the session command history."""
        if not self.inputs.history:
            self.out("History is empty.")
            return
        for index, line in enumerate(self.inputs.history, start=1):
            self.out(f"  {index:>3}  {line}")

    def cmd_help(self, args: List[str]) -> None:
        """Print the command help."""
        self.out(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop; state is saved during shutdown."""
        globalvar.set_value("system_running", False)


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None, help="path to a JSON config file")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    options = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if options.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    app = DispatchApp()
    app.start(options.config)
    app.loop()
    app.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
