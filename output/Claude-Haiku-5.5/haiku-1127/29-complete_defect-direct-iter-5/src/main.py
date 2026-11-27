"""Command-line entry point for the Food Delivery Order Dispatch simulator.

Run with ``python src/main.py`` from the project root. The main loop reads a
command each iteration; ``step n`` advances the simulation by ``n`` ticks,
where each tick is one loop iteration of the simulated clock.
"""

import logging
import sys
from typing import Callable, List, Optional, Sequence

import globalvar
from config import DEFAULT_CONFIG_PATH, DEFAULT_STATE_PATH, load_config, write_json
from display import DisplayManager
from input_manager import InputManager
from system import SystemManager, init_system

MAX_STEPS = 10000
LOG_FILE = "dispatch.log"

logger = logging.getLogger("dispatch")


def configure_logging() -> None:
    """Configure file logging for debugging and diagnostics."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


class DispatchApp:
    """Interactive controller that connects commands to the system."""

    def __init__(self, params: Optional[dict] = None,
                 input_func: Optional[Callable[[str], str]] = None,
                 output_func: Optional[Callable[[str], None]] = None) -> None:
        """Create the application.

        Args:
            params: System parameters loaded from the configuration file.
            input_func: Optional replacement for ``input``.
            output_func: Optional replacement for ``print``.
        """
        self.out = output_func or print
        self.system: SystemManager = init_system(params)
        self.display = DisplayManager()
        self.inputs = InputManager(input_func, output_func)

    # ----------------------------------------------------------- main loop
    def run(self) -> None:
        """Run the interactive loop until the system stops."""
        self.out("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while globalvar.get_value("running"):
            try:
                command, args = self.inputs.read_command()
            except (EOFError, KeyboardInterrupt):
                self.out("\nExiting.")
                break
            if not command:
                continue
            try:
                self.dispatch(command, args)
            except Exception as exc:  # error recovery: keep the loop alive
                logger.exception("Command '%s' failed", command)
                self.out(f"Error: {exc}. The system state is preserved; please try again.")
            problems = self.system.verify_consistency()
            if problems:
                self.out("Recovered from inconsistent state: " + "; ".join(problems))

    def dispatch(self, command: str, args: List[str]) -> None:
        """Route a command name to its handler.

        Args:
            command: Normalised command name.
            args: Command arguments.
        """
        handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "step": self.cmd_step,
            "save": self.cmd_save,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }
        handler = handlers.get(command)
        if handler is None:
            self.out(f"Unknown command '{command}'. Type 'help' for the list of commands.")
            return
        handler(args)

    # ------------------------------------------------------------ commands
    def cmd_start(self, args: List[str]) -> None:
        """Place an order and report the assignment and planned route.

        Args:
            args: Optional four coordinates; if empty the user is prompted.
        """
        if args:
            try:
                coords: Optional[List[int]] = self.inputs.parse_coordinates(args)
            except ValueError as exc:
                self.out(f"Invalid input: {exc}.")
                return
        else:
            coords = self.inputs.prompt_coordinates()
        if coords is None:
            self.out("Order cancelled.")
            return
        try:
            result = self.system.submit_order(coords)
        except ValueError as exc:
            self.out(f"Invalid order: {exc}.")
            return

        order = result["order"]
        rx, ry, cx, cy = coords
        rcol, rrow = order.res_center
        ccol, crow = order.cus_center
        self.out(f"Order #{order.id} created at tick {order.start_tick}.")
        self.out(f"Restaurant input ({rx},{ry}) -> grid center ({rcol},{rrow})")
        self.out(f"Customer input ({cx},{cy}) -> grid center ({ccol},{crow})")
        if result["new_riders"]:
            ids = ", ".join(str(r.rider_id) for r in result["new_riders"])
            self.out(f"New rider(s) recruited: {ids}.")
        else:
            self.out("No new rider added.")

        rider = result["rider"]
        if rider is None:
            self.out("No rider available; the order is pending until a rider joins.")
            return
        self.out(f"Assigned to rider {rider.rider_id} (state: {rider.state_name()}).")
        self.out(self.display.format_route(rider.speed, result["distance"], result["eta_ticks"]))
        route_points = [(px, py) for px, py, _ in result["route"]]
        self.out(self.display.render_map(self.system.riders, [order], route_points))

    def cmd_status(self, args: List[str]) -> None:
        """Print funds, rider count and each rider's state and orders."""
        self.out(self.display.format_status(
            self.system.funds,
            self.system.tick_count,
            self.system.riders,
            self.system.order_manager.pending_count,
        ))

    def cmd_orders(self, args: List[str]) -> None:
        """Print the table of all orders."""
        self.out(self.display.format_orders(self.system.orders))

    def cmd_riders(self, args: List[str]) -> None:
        """Print every recorded rider status change."""
        self.out(self.display.format_rider_logs(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map with riders and active orders."""
        self.out(self.display.render_map(self.system.riders, self.system.active_orders()))

    def cmd_step(self, args: List[str]) -> None:
        """Advance the simulation by one or more ticks.

        Args:
            args: Optional number of ticks (1-10000).
        """
        try:
            count = InputManager.parse_positive_int(args, 1, MAX_STEPS)
        except ValueError as exc:
            self.out(f"Invalid input: {exc}.")
            return
        for _ in range(count):
            before = {r.rider_id: len(r.log) for r in self.system.riders}
            self.system.tick()
            for rider in self.system.riders:
                for entry in rider.log[before.get(rider.rider_id, 0):]:
                    order_text = entry["order_id"] if entry["order_id"] is not None else "-"
                    self.out(f"  [tick {entry['tick']}] rider {rider.rider_id}: "
                             f"{entry['event']} (order {order_text})")
        active = len(self.system.active_orders())
        self.out(f"Tick {self.system.tick_count}: funds={self.system.funds}, "
                 f"riders={len(self.system.riders)}, active orders={active}")

    def cmd_save(self, args: List[str]) -> None:
        """Save the system snapshot to a JSON file.

        Args:
            args: Optional destination path.
        """
        path = args[0] if args else DEFAULT_STATE_PATH
        try:
            write_json(path, self.system.snapshot())
        except OSError as exc:
            self.out(f"Could not save to {path}: {exc}")
            return
        self.out(f"System state saved to {path}.")

    def cmd_help(self, args: List[str]) -> None:
        """Print the command list."""
        self.out(self.inputs.help_text())

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.shutdown()
        self.out("Goodbye.")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Unused command-line arguments (reserved for future options).

    Returns:
        Process exit code.
    """
    configure_logging()
    params = load_config(DEFAULT_CONFIG_PATH)
    app = DispatchApp(params=params)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
