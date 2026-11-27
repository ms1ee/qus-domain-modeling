"""Command-line entry point for the food delivery dispatch simulator.

Run with:  python src/main.py [--config dispatch_config.json]
"""

import argparse
import logging
import sys
from typing import Callable, Dict, List, Optional

from display import DisplayManager
from input_manager import InputManager
from system import SystemManager, init_system

logger = logging.getLogger("dispatch")

DEFAULT_STATE_FILE = "dispatch_state.json"
MAX_TICKS_PER_COMMAND = 10000

BANNER = (
    "Food Delivery Order Dispatch System\n"
    "Type 'help' for commands. Grid: 8x8 cells of 100 units (0-800)."
)


class DispatchApp:
    """Interactive command loop tying together all managers."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
    ) -> None:
        """Create the application.

        Args:
            config_path: Optional JSON configuration file path.
            input_func: Function used to read commands.
            output_func: Function used to print output.
        """
        self.config_path = config_path
        self.input_func = input_func
        self.output = output_func
        self.inputs = InputManager()
        self.system: Optional[SystemManager] = None
        self.display: Optional[DisplayManager] = None
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "tick": self._cmd_tick,
            "save": self._cmd_save,
            "load": self._cmd_load,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
        }

    def start(self) -> None:
        """Initialise the system and run the command loop."""
        init_system(self.config_path)
        self.system = SystemManager()
        self.display = DisplayManager(self.system)
        self.output(BANNER)
        self.run_loop()

    def run_loop(self) -> None:
        """Read, validate and execute commands until the system stops."""
        while self.system.is_running():
            try:
                raw = self.input_func("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self.output("")
                self.system.stop()
                break
            line = raw.strip()
            if not line:
                continue
            try:
                line = self.inputs.expand_history(line)
                self.inputs.record(line)
                self.execute(line)
            except ValueError as exc:
                self.output(f"Error: {exc}")
            except Exception as exc:  # error recovery: keep the loop alive
                logger.exception("unexpected error while executing '%s'", line)
                self.output(f"Unexpected error: {exc}. Recovering system state.")
                self.recover()

    def execute(self, line: str) -> None:
        """Parse and run a single command line.

        Args:
            line: Command text (already history-expanded).

        Raises:
            ValueError: For unknown commands or invalid arguments.
        """
        command, args = self.inputs.parse_command(line)
        self._handlers[command](args)

    def recover(self) -> None:
        """Run the consistency check and report any repairs."""
        if self.system is None:
            return
        issues = self.system.check_consistency()
        for issue in issues:
            self.output(f"Recovered: {issue}")

    # ----- command handlers ------------------------------------------
    def _cmd_start(self, args: List[str]) -> None:
        """Place a new order and dispatch it."""
        if args:
            coords = self.inputs.parse_coordinates(args)
        else:
            coords = self.inputs.read_coordinates(self.input_func, self.output)
        order = self.system.order_manager.create_order(coords)
        rider, recruited = self.system.dispatch_order(order)
        self.output(self.display.format_new_order(order, rider, recruited))

    def _cmd_status(self, args: List[str]) -> None:
        """Show the system status snapshot."""
        issues = self.system.check_consistency()
        self.output(self.display.format_status(issues))

    def _cmd_orders(self, args: List[str]) -> None:
        """Show details of every order."""
        self.output(self.display.format_orders())

    def _cmd_riders(self, args: List[str]) -> None:
        """Show the rider status change log."""
        self.output(self.display.format_rider_log())

    def _cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map."""
        self.output(self.display.render_map())

    def _cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation clock."""
        count = 1
        if args:
            count = InputManager.parse_integer(args[0], "tick count")
            if not 1 <= count <= MAX_TICKS_PER_COMMAND:
                raise ValueError(f"tick count must be between 1 and {MAX_TICKS_PER_COMMAND}")
        completed = self.system.run_ticks(count)
        self.output(
            f"Advanced {count} tick(s). Current tick: {self.system.current_tick}. "
            f"Orders completed in this step: {completed}. Funds: {self.system.funds}."
        )

    def _cmd_save(self, args: List[str]) -> None:
        """Save the state to a JSON file."""
        path = args[0] if args else DEFAULT_STATE_FILE
        self.system.save_state(path)
        self.output(f"State saved to {path}.")

    def _cmd_load(self, args: List[str]) -> None:
        """Load the state from a JSON file."""
        path = args[0] if args else DEFAULT_STATE_FILE
        self.system.load_state(path)
        self.output(f"State loaded from {path}.")

    def _cmd_history(self, args: List[str]) -> None:
        """List previously entered commands."""
        history = self.inputs.history
        if not history:
            self.output("No command history yet.")
            return
        self.output("\n".join(f"{i}: {cmd}" for i, cmd in enumerate(history, start=1)))

    def _cmd_help(self, args: List[str]) -> None:
        """Show command help."""
        self.output(InputManager.HELP_TEXT)

    def _cmd_quit(self, args: List[str]) -> None:
        """Exit the program."""
        self.system.stop()
        self.output("Goodbye.")


def main(argv: Optional[List[str]] = None) -> int:
    """Parse arguments, configure logging and run the application.

    Args:
        argv: Optional argument list (defaults to sys.argv).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default="dispatch_config.json",
                        help="JSON configuration file (optional)")
    parser.add_argument("--log-file", default="dispatch.log",
                        help="file used for debug/log output")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        filename=args.log_file,
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = DispatchApp(config_path=args.config)
    app.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
