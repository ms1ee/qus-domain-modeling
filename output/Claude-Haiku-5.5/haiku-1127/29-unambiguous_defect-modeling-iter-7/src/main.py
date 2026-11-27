"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys
from typing import Callable, Dict, List, Optional

from config import SystemConfig
from display import DisplayManager
from input_manager import InputManager
from system import SystemManager, init_system

LOGGER = logging.getLogger("dispatch")

BANNER = (
    "=== Food Delivery Order Dispatch System ===\n"
    "Type 'help' for commands. Map: 8x8 grid, 800x800 units."
)

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Submit an order (restaurant then customer, 0-800)
  status  (st)         Show funds, riders and their orders
  orders  (o)          Show all order details
  riders  (r)          Show every rider status-change record
  map     (m)          Show the ASCII map
  tick [n]  (t)        Advance the simulation by n ticks (default 1)
  history  (h)         Show command history
  help  (?)            Show this help
  quit  (exit, q)      Save state and exit
Shortcuts: !! repeats the last command, !n repeats history entry n."""


class DispatchCLI:
    """Interactive command loop tying all components together.

    Attributes:
        system: The simulation core.
        inputs: Command parser and history.
        display: Renderer for text output.
        config: Configuration/persistence helper.
        persist: Whether to save state on exit.
    """

    PROMPT = "dispatch> "

    def __init__(
        self,
        system: SystemManager,
        inputs: InputManager,
        display: DisplayManager,
        config: SystemConfig,
        persist: bool = True,
    ) -> None:
        """Create the command-line interface.

        Args:
            system: Simulation core.
            inputs: Input manager.
            display: Display manager.
            config: Configuration helper.
            persist: Save state to the configuration file on exit.
        """
        self.system = system
        self.inputs = inputs
        self.display = display
        self.config = config
        self.persist = persist
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
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

    def run(self) -> None:
        """Run the interactive loop until the system stops.

        Returns:
            None
        """
        print(BANNER)
        while self.system.running_state:
            try:
                raw = input(self.PROMPT)
            except (EOFError, KeyboardInterrupt):
                print()
                self.cmd_quit([])
                break
            try:
                line = self.inputs.expand(raw)
            except ValueError as exc:
                print(f"Error: {exc}")
                continue
            if not line:
                continue
            self.inputs.record(line)
            try:
                self.dispatch(line)
            except ValueError as exc:
                print(f"Error: {exc}")
            except Exception:  # Keep the simulation alive on unexpected errors.
                LOGGER.exception("Unexpected error while handling %r", line)
                print("Internal error occurred; system state was preserved. See log.")

    def dispatch(self, line: str) -> None:
        """Parse and execute one command line.

        Args:
            line: Command text.

        Returns:
            None
        """
        command, args = self.inputs.parse(line)
        if not command:
            return
        self._handlers[command](args)

    def cmd_start(self, args: List[str]) -> None:
        """Submit a new order.

        Args:
            args: Optional four coordinates; prompted for when omitted.

        Returns:
            None
        """
        tokens = args
        if not tokens:
            try:
                tokens = input("Enter restaurant_x restaurant_y customer_x customer_y: ").split()
            except (EOFError, KeyboardInterrupt):
                print()
                return
        coords = self.inputs.parse_coordinates(tokens, 4)
        result = self.system.submit_order((coords[0], coords[1]), (coords[2], coords[3]))
        print(self.display.render_order_summary(result))
        print(
            self.display.render_map(
                self.system.riders,
                self.system.order_manager.orders,
                result["route"],
            )
        )
        print(self.display.render_legend())

    def cmd_status(self, args: List[str]) -> None:
        """Show the system status snapshot.

        Args:
            args: Unused.

        Returns:
            None
        """
        print(self.display.render_status(self.system))

    def cmd_orders(self, args: List[str]) -> None:
        """Show all order details.

        Args:
            args: Unused.

        Returns:
            None
        """
        print(self.display.render_orders(self.system.order_manager.orders))

    def cmd_riders(self, args: List[str]) -> None:
        """Show every rider's status-change log.

        Args:
            args: Unused.

        Returns:
            None
        """
        print(self.display.render_rider_logs(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map with riders and active orders.

        Args:
            args: Unused.

        Returns:
            None
        """
        print(
            self.display.render_map(self.system.riders, self.system.order_manager.orders)
        )
        print(self.display.render_legend())

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation.

        Args:
            args: Optional number of ticks.

        Returns:
            None
        """
        count = self.inputs.parse_tick_count(args)
        issues = self.system.run_ticks(count)
        active = len(self.system.order_manager.active_orders())
        print(f"Advanced {count} tick(s). Current tick: {self.system.current_tick}. "
              f"Active orders: {active}.")
        for issue in issues:
            print(f"Warning: {issue}")

    def cmd_history(self, args: List[str]) -> None:
        """Print command history.

        Args:
            args: Unused.

        Returns:
            None
        """
        if not self.inputs.command_history:
            print("History is empty.")
            return
        for index, command in enumerate(self.inputs.command_history, start=1):
            print(f"{index:>4}  {command}")

    def cmd_help(self, args: List[str]) -> None:
        """Print help text.

        Args:
            args: Unused.

        Returns:
            None
        """
        print(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Save state (when enabled) and stop the main loop.

        Args:
            args: Unused.

        Returns:
            None
        """
        if self.system.running_state and self.persist:
            try:
                path = self.config.save(self.system.snapshot())
                print(f"State saved to {path}.")
            except OSError as exc:
                print(f"Warning: could not save state: {exc}")
        self.system.shutdown()
        print("Goodbye.")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        argparse.Namespace: Parsed options.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default="config.json", help="JSON configuration file")
    parser.add_argument("--no-save", action="store_true", help="do not save state on exit")
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="logging verbosity",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point.

    Args:
        argv: Optional argument list.

    Returns:
        int: Process exit code.
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = SystemConfig(args.config)
    parameters = config.load()
    system = init_system(parameters)
    cli = DispatchCLI(
        system=system,
        inputs=InputManager(),
        display=DisplayManager(),
        config=config,
        persist=not args.no_save,
    )
    cli.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
