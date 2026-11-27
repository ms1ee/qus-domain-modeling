"""Command-line entry point for the food delivery dispatch simulator.

Run with:  python src/main.py [config.json]
"""

import logging
import os
import sys

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from display import DisplayManager  # noqa: E402
from input_manager import InputError, InputManager  # noqa: E402
from system import SystemManager, init_system  # noqa: E402

logger = logging.getLogger("dispatch")

BANNER = (
    "Food Delivery Order Dispatch System\n"
    "Type 'help' for commands, 'quit' to exit."
)
MAX_MANUAL_TICKS = 10000
DEFAULT_STATE_FILE = "simulation_state.json"


class Application:
    """Wires the system, display and input managers into a CLI loop."""

    def __init__(self, system: SystemManager, display: DisplayManager,
                 inputs: InputManager) -> None:
        """Create the application.

        Args:
            system: Core simulation facade.
            display: Text and map renderer.
            inputs: Command reader, parser and history.
        """
        self.system = system
        self.display = display
        self.inputs = inputs
        self._handlers = {
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

    def run(self) -> None:
        """Run the interactive loop until the system stops."""
        print(BANNER)
        while self.system.is_running:
            try:
                line = self.inputs.read_line()
            except (EOFError, KeyboardInterrupt):
                print()
                self.system.is_running = False
                break
            if not line:
                continue
            try:
                line = self.inputs.expand_shortcut(line)
                name, args = self.inputs.parse_command(line)
                self.inputs.record(line)
                self._handlers[name](args)
            except InputError as exc:
                print(f"Input error: {exc}")
            except RuntimeError as exc:
                print(f"Simulation error: {exc}")
            except Exception:  # keep the session alive on unexpected faults
                logger.exception("Unexpected failure while handling command")
                print("An unexpected error occurred; system state preserved.")
        print("Goodbye.")

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def cmd_start(self, args) -> None:
        """Place an order and simulate its delivery."""
        if args:
            coords = InputManager.parse_coordinates(args)
        else:
            line = self.inputs.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y: ")
            coords = InputManager.parse_coordinates(line.split())

        rx, ry, cx, cy = coords
        order, rider, added = self.system.submit_order((rx, ry), (cx, cy))

        print(f"Restaurant grid position: {order.restaurant_pos}")
        print(f"Customer grid position:   {order.customer_pos}")
        print(f"New rider added: {'yes' if added else 'no'}")
        if rider is None:
            print("No rider is available and funds are insufficient; "
                  "the order is pending.")
            return

        print(f"Assigned rider: {rider.rider_id} (speed {rider.speed} units/tick)")
        print(self.display.render_route(order.route, rider.speed))
        print(self.display.render_map(self.system.riders, [order], order.route))

        ticks = self.system.run_until_order_complete(order)
        print(f"Order {order.id} delivered in {ticks} ticks "
              f"(distance {order.distance:.1f}).")

    def cmd_status(self, _args) -> None:
        """Show funds, riders and consistency warnings."""
        print(self.display.render_status(
            self.system.funds, self.system.riders,
            self.system.check_consistency()))

    def cmd_orders(self, _args) -> None:
        """Show the order table."""
        print(self.display.render_orders(self.system.orders))

    def cmd_riders(self, _args) -> None:
        """Show the event log of every rider."""
        print(self.display.render_rider_logs(self.system.riders))

    def cmd_map(self, _args) -> None:
        """Show the ASCII map."""
        print(self.display.render_map(self.system.riders, self.system.orders))

    def cmd_tick(self, args) -> None:
        """Advance the simulation by one or more ticks."""
        count = InputManager.parse_positive_int(args, 1, MAX_MANUAL_TICKS)
        for _ in range(count):
            self.system.tick()
        print(f"Advanced {count} tick(s); current time {self.system.tick_count}.")

    def cmd_save(self, args) -> None:
        """Persist the simulation state to a JSON file."""
        path = args[0] if args else DEFAULT_STATE_FILE
        self.system.save_state(path)
        print(f"State saved to {path}.")

    def cmd_history(self, _args) -> None:
        """Print the command history."""
        if not self.inputs.command_history:
            print("History is empty.")
            return
        for index, entry in enumerate(self.inputs.command_history, start=1):
            print(f"  {index:>3}  {entry}")

    def cmd_help(self, _args) -> None:
        """Print the command reference."""
        print(self.display.render_help())

    def cmd_quit(self, _args) -> None:
        """Stop the main loop."""
        self.system.is_running = False


def main(argv=None) -> int:
    """Program entry point.

    Args:
        argv: Optional argument list; the first element may be a config path.

    Returns:
        Process exit code.
    """
    argv = sys.argv[1:] if argv is None else list(argv)
    level_name = os.environ.get("DISPATCH_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    if not isinstance(level, int):
        level = logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config_path = argv[0] if argv else os.path.join(os.getcwd(), "config.json")
    system = init_system(config_path)
    app = Application(system, DisplayManager(), InputManager())
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
