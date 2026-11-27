"""Command-line entry point for the food delivery dispatch simulator.

Run with:  python src/main.py [--debug]

Commands (shortcut in brackets):
    start [rx ry cx cy]  [s]   create an order and show the assigned route
    status               [st]  funds, riders and their orders
    orders               [o]   table of all orders
    riders               [r]   status-change log for every rider
    map                  [m]   ASCII map with riders and active orders
    tick [n]             [t]   advance the simulation by n ticks
    save [path]          [w]   write the system state to JSON
    history              [h]   list recent commands
    !!                         repeat the previous command
    help                 [?]   show help
    quit | exit          [q]   leave the program
"""

from __future__ import annotations

import logging
import sys
from typing import Callable, Dict, List, Optional, Sequence

import globalvar
from display import DisplayManager
from input_manager import InputManager
from order_model import COMPLETED
from path_planner import PathPlanner, estimate_ticks, route_length
from system import SystemManager, init_system

LOG_FILE = "dispatch.log"
CONFIG_FILE = "dispatch_config.json"
STATE_FILE = "dispatch_state.json"
PROMPT = "dispatch> "

BANNER = (
    "=====================================================\n"
    "  Food Delivery Order Dispatch System (8x8 grid sim)\n"
    "====================================================="
)

HELP_TEXT = """Commands:
  start [rx ry cx cy] (s)  Create an order; coordinates 0-1000 (prompts if omitted)
  status (st)              System funds and rider status
  orders (o)               All orders with timing and assignment
  riders (r)               Status-change log for every rider
  map (m)                  ASCII map (R=rider S=restaurant C=customer #=street)
  tick [n] (t)             Advance the simulation by n ticks (default 1)
  save [path] (w)          Save state to JSON (default dispatch_state.json)
  history (h)              Show recent commands
  !!                       Repeat the previous command
  help (?)                 Show this help
  quit / exit (q)          Leave the program"""

logger = logging.getLogger("dispatch")


def configure_logging(debug: bool = False) -> None:
    """Send diagnostic logs to ``dispatch.log``.

    Args:
        debug: When True, log at DEBUG level instead of INFO.
    """
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


class DispatchApp:
    """Interactive command loop that ties all modules together."""

    def __init__(self, config_path: str = CONFIG_FILE) -> None:
        """Initialise the system and the interaction components.

        Args:
            config_path: Optional JSON configuration file.
        """
        self.system: SystemManager = init_system(config_path)
        self.display = DisplayManager()
        self.inputs = InputManager()
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
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
            "unknown": self._cmd_unknown,
        }

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self) -> int:
        """Run the interactive loop until the user quits or input ends.

        Returns:
            Process exit code (0 on normal exit).
        """
        print(BANNER)
        self._cmd_help([])
        while self.system.running:
            line = self.inputs.read_line(PROMPT)
            if line is None:
                print()
                break
            line = line.strip()
            if not line:
                continue
            if line == "!!":
                last = self.inputs.last_command()
                if last is None:
                    print("No previous command to repeat.")
                    continue
                print(f"Repeating: {last}")
                line = last
            self.inputs.record(line)
            command, args = self.inputs.resolve(line)
            handler = self._handlers.get(command, self._cmd_unknown)
            try:
                handler(args)
            except ValueError as exc:
                print(f"Input error: {exc}")
            except Exception:  # noqa: BLE001 - keep the session alive
                logger.exception("Command failed: %s", line)
                print("Unexpected internal error; state preserved. See dispatch.log.")
        self.system.shutdown()
        print("Goodbye.")
        return 0

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _active_orders(self):
        """Return orders that are not yet completed."""
        return [o for o in self.system.order_manager.orders if o.status != COMPLETED]

    def _completed_count(self) -> int:
        """Return the number of completed orders."""
        return sum(1 for o in self.system.order_manager.orders if o.status == COMPLETED)

    def _prompt_coordinates(self) -> Optional[List[str]]:
        """Ask the user for four coordinates; None means cancelled."""
        text = self.inputs.read_line(
            "Enter restaurant x y and customer x y (0-1000, blank to cancel): "
        )
        if text is None or not text.strip():
            return None
        return text.split()

    # ------------------------------------------------------------------ #
    # Command handlers
    # ------------------------------------------------------------------ #
    def _cmd_start(self, args: List[str]) -> None:
        """Create an order, assign it and show the route for the rider."""
        raw = args if args else self._prompt_coordinates()
        if raw is None:
            print("Order entry cancelled.")
            return
        values = self.inputs.validate_coordinates(self.inputs.parse_coordinates(raw))
        order = self.system.order_manager.create_order(values)
        rider, recruited = self.system.submit_order(order)

        print(f"Order #{order.id} created at tick {order.start_time}")
        print(f"Restaurant grid corner: ({order.res_pos[0]}, {order.res_pos[1]})")
        print(f"Customer grid corner:   ({order.cus_pos[0]}, {order.cus_pos[1]})")
        if recruited:
            newest = self.system.riders[-1]
            print(f"New rider added: yes (Rider #{newest.rider_id}, funds now {self.system.funds})")
        else:
            print("New rider added: no")

        if rider is None:
            print(
                "No rider is available and recruitment is not possible "
                f"(funds {self.system.funds}). Order is queued as pending."
            )
            return

        route = PathPlanner.plan_route(rider.position, [order.res_pos, order.cus_pos])
        length = route_length(route)
        ticks = estimate_ticks(length, rider.speed)
        print(
            f"Assigned rider: #{rider.rider_id} (state: {rider.state_name}, "
            f"active orders: {len(rider.active_orders())})"
        )
        print(
            f"Rider speed: {rider.speed} units/tick | route length: {length} units | "
            f"estimated time: {ticks} ticks"
        )
        print(self.display.render_route(route, rider.speed))
        print(self.display.render_map([rider], [order], route))

    def _cmd_status(self, args: List[str]) -> None:
        """Show the system snapshot."""
        print(f"System funds: {self.system.funds}")
        print(f"Simulation tick: {self.system.sim_time}")
        print(self.display.render_status(self.system.riders, len(self.system.pending_orders)))
        issues = self.system.check_consistency()
        if issues:
            print("Consistency warnings:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("Consistency check: OK")

    def _cmd_orders(self, args: List[str]) -> None:
        """Show all orders."""
        print(self.display.render_orders(self.system.order_manager.orders))

    def _cmd_riders(self, args: List[str]) -> None:
        """Show the status-change log for all riders."""
        print(self.display.render_rider_log(self.system.riders))

    def _cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map."""
        print(self.display.render_map(self.system.riders, self._active_orders()))

    def _cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation."""
        count = self.inputs.parse_count(args)
        before = self._completed_count()
        for _ in range(count):
            self.system.tick()
        done = self._completed_count() - before
        print(
            f"Advanced {count} tick(s); now at tick {self.system.sim_time}. "
            f"Orders completed in this run: {done}. "
            f"Pending orders: {len(self.system.pending_orders)}."
        )

    def _cmd_save(self, args: List[str]) -> None:
        """Persist the system state to JSON."""
        path = args[0] if args else STATE_FILE
        try:
            self.system.save_state(path)
            print(f"State saved to {path}")
        except OSError as exc:
            print(f"Could not save state: {exc}")

    def _cmd_history(self, args: List[str]) -> None:
        """List recent commands."""
        if not self.inputs.history:
            print("History is empty.")
            return
        for index, line in enumerate(self.inputs.history[-20:], start=1):
            print(f"  {index:>2}. {line}")

    def _cmd_help(self, args: List[str]) -> None:
        """Show command help."""
        print(HELP_TEXT)

    def _cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.shutdown()

    def _cmd_unknown(self, args: List[str]) -> None:
        """Handle unrecognised commands."""
        print("Unknown command. Type 'help' to see the available commands.")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Optional argument list; ``--debug`` enables verbose logging.

    Returns:
        Process exit code.
    """
    arguments = list(argv) if argv is not None else sys.argv[1:]
    configure_logging(debug="--debug" in arguments)
    app = DispatchApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
