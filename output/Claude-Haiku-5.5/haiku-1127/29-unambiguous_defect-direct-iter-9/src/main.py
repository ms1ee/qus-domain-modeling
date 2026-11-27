"""Command-line entry point for the food delivery dispatch simulator.

Run from the ``src`` directory (or with ``src`` on ``PYTHONPATH``):

    python main.py            # normal mode
    python main.py --debug    # verbose logging to dispatch.log
"""

import logging
import sys
from typing import Callable, List, Optional

from config import CONFIG_FILE, LOG_FILE, STATE_FILE
from display import DisplayManager
from input_manager import InputError, InputManager
from order import OrderManager
from persistence import load_config, save_state
from system import init_system

try:  # Enables arrow-key history on platforms that provide readline.
    import readline  # noqa: F401
except ImportError:
    readline = None

logger = logging.getLogger("dispatch.main")

HELP_TEXT = """Commands (shortcut in brackets):
  start   [n]  Enter order: restaurant x y and customer x y (0-800 integers).
               Example: start 100 200 500 600   (or 'start' then prompts)
  status  [s]  Show system funds, tick, and each rider's state and orders.
  orders  [o]  Show all orders with start tick, locations, distance, time, rider.
  riders  [r]  Show every recorded status change of every rider.
  map     [m]  Show the 8x8 ASCII map with riders and active orders.
  tick    [t]  Advance the simulation by N ticks (default 1, max 1000).
  history [ ]  Show recently entered commands.
  help    [h]  Show this help text.
  quit    [q]  Save state and exit (also: exit, x)."""


class DispatchApp:
    """Interactive application wiring input, system state and display."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[..., None] = print,
        config_path: str = CONFIG_FILE,
        state_path: str = STATE_FILE,
    ) -> None:
        """Initialise the system from configuration and build command handlers.

        Args:
            input_func: Function used to read user input.
            output_func: Function used to print output.
            config_path: JSON configuration file path.
            state_path: JSON file where state is saved on exit.
        """
        self.out = output_func
        self.inputs = InputManager(input_func)
        self.display = DisplayManager()
        self.orders = OrderManager()
        self.state_path = state_path
        self.system = init_system(load_config(config_path))
        self.handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> int:
        """Run the command loop until the user quits.

        Returns:
            Process exit code (0 on normal exit).
        """
        self.out("Food delivery dispatch simulator. Type 'help' for commands.")
        while self.system.is_running():
            try:
                line = self.inputs.read_line("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self.out("")
                break
            self.execute(line)
        self.shutdown()
        return 0

    def execute(self, line: str) -> None:
        """Parse and run a single command line with error recovery."""
        try:
            command, args = self.inputs.parse_command(line)
        except InputError as exc:
            self.out(f"Error: {exc}")
            return
        if command is None:
            return
        try:
            self.handlers[command](args)
        except InputError as exc:
            self.out(f"Error: {exc}")
        except Exception as exc:  # Recovery: keep the simulator running.
            logger.exception("Command '%s' failed", command)
            self.out(f"Unexpected error while running '{command}': {exc}")
            for issue in self.system.consistency_check():
                self.out(f"  Recovered: {issue}")

    def shutdown(self) -> None:
        """Save the state file and report the outcome."""
        if save_state(self.system, self.state_path):
            self.out(f"State saved to {self.state_path}.")
        else:
            self.out("Warning: state could not be saved.")
        self.out("Goodbye.")

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def cmd_start(self, args: List[str]) -> None:
        """Create and assign an order, then show the route map."""
        if args:
            restaurant, customer = self.inputs.parse_coordinates(" ".join(args))
        else:
            pair = self.inputs.prompt_order()
            if pair is None:
                self.out("Order entry cancelled.")
                return
            restaurant, customer = pair

        order = self.orders.create_order(restaurant, customer)
        try:
            result = self.orders.assign_order(order)
        except RuntimeError as exc:
            self.out(f"Order {order.id} could not be assigned: {exc}.")
            return

        rider = result["rider"]
        self.out(f"Order {order.id} accepted.")
        self.out(f"  Restaurant grid position : {order.res_pos} "
                 f"(entered {restaurant})")
        self.out(f"  Customer grid position   : {order.cus_pos} "
                 f"(entered {customer})")
        self.out(f"  New rider added          : {'yes' if result['new_rider'] else 'no'}")
        self.out(f"  Assigned rider           : {rider.rider_id} "
                 f"(speed {rider.speed} units/tick)")
        self.out(f"  Route distance           : {result['distance']} units")
        self.out(f"  Estimated time           : {result['eta_ticks']} tick(s)")
        self.out("Route map (planned from the rider's current position):")
        self.out(self.display.render_map(
            riders=self.system.riders,
            orders=[order],
            route=result["route"],
        ))

    def cmd_status(self, args: List[str]) -> None:
        """Show the system snapshot and any consistency issues."""
        issues = self.system.consistency_check()
        self.out(self.display.render_status(self.system))
        for issue in issues:
            self.out(f"  Recovered: {issue}")

    def cmd_orders(self, args: List[str]) -> None:
        """Show the order table."""
        self.out(self.display.render_orders(self.orders.all_orders()))

    def cmd_riders(self, args: List[str]) -> None:
        """Show every rider's recorded status changes."""
        self.out(self.display.render_rider_log(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map with riders and active orders."""
        self.out(self.display.render_map(
            riders=self.system.riders,
            orders=self.orders.active_orders(),
        ))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation and report arrival and delivery events."""
        steps = self.inputs.parse_tick_count(args)
        for _ in range(steps):
            for event in self.system.tick():
                self.out(self.display.render_event(event))
        self.out(f"Advanced {steps} tick(s). Current tick: {self.system.tick_count}. "
                 f"Funds: {self.system.funds}")

    def cmd_history(self, args: List[str]) -> None:
        """Show the most recent entered lines."""
        recent = self.inputs.history[-20:]
        if not recent:
            self.out("No history yet.")
            return
        for index, line in enumerate(recent, start=max(len(self.inputs.history) - 20, 0) + 1):
            self.out(f"  {index:>4}  {line}")

    def cmd_help(self, args: List[str]) -> None:
        """Show the command reference."""
        self.out(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.stop()


def main(argv: Optional[List[str]] = None) -> int:
    """Configure logging and run the interactive simulator.

    Args:
        argv: Command-line arguments (excluding the program name).

    Returns:
        Process exit code.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    level = logging.DEBUG if "--debug" in argv else logging.INFO
    logging.basicConfig(
        filename=LOG_FILE,
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = DispatchApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
