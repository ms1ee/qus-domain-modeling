"""Command-line entry point for the Food Delivery Order Dispatch simulator.

Each successfully executed command advances simulated time by one tick,
except ``help``, ``history``, ``save``, ``tick`` (which advances by its own
count) and ``quit``.
"""

import logging
import sys
from typing import Any, Callable, Dict, List

import globalvar
from display import DisplayManager
from input_manager import InputError, InputManager
from order import OrderManager
from system import init_system

LOG_FILE = "dispatch.log"
DEFAULT_SAVE_FILE = "dispatch_state.json"

logger = logging.getLogger("dispatch")

BANNER = """==============================================
 Food Delivery Order Dispatch Simulator
 Type 'help' for commands, 'quit' to exit.
=============================================="""

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant then customer, 0-1000).
                       Prompts for the four values if omitted. Shortcut: n
  status (st)          Show system funds, riders and their order lists
  orders (o)           Show all orders with delivery details
  riders (r)           Show the status-change log of every rider
  map (m)              Show the ASCII map (R rider, S restaurant, C customer)
  tick [n] (t)         Advance simulated time by n ticks (default 1)
  save [file]          Save state as JSON (default dispatch_state.json)
  history              Show command history
  !!                   Repeat the last command
  help (h, ?)          Show this help
  quit (q, exit)       Exit the program
Each executed command (except help/history/save/tick/quit) advances time by one tick."""


class DispatchApp:
    """Interactive application wiring the managers together.

    Attributes:
        system: SystemManager holding funds, riders and simulated time.
        orders: OrderManager for order creation and assignment.
        display: DisplayManager for text and map output.
        inputs: InputManager for parsing and validation.
    """

    def __init__(self) -> None:
        """Initialise the global state and all managers."""
        self.system = init_system()
        self.orders = OrderManager(self.system)
        self.display = DisplayManager(self.system)
        self.inputs = InputManager()
        self._handlers: Dict[str, Callable[[List[str]], bool]] = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "tick": self._cmd_tick,
            "save": self._cmd_save,
            "history": self._cmd_history,
            "help": self._cmd_help,
        }

    # ------------------------------------------------------------------
    # Command handlers: each returns True if the command advances time.
    # ------------------------------------------------------------------
    def _cmd_start(self, args: List[str]) -> bool:
        tokens = args
        if not tokens:
            raw = self.inputs.read_line(
                "Enter restaurant_x restaurant_y customer_x customer_y: "
            )
            tokens = self.inputs.split_tokens(raw)
        res_x, res_y, cus_x, cus_y = self.inputs.parse_coordinates(tokens)
        result = self.orders.submit(res_x, res_y, cus_x, cus_y)
        print(self.display.render_start_result(result))
        return True

    def _cmd_status(self, args: List[str]) -> bool:
        print(self.display.render_status())
        return True

    def _cmd_orders(self, args: List[str]) -> bool:
        print(self.display.render_orders())
        return True

    def _cmd_riders(self, args: List[str]) -> bool:
        print(self.display.render_rider_log())
        return True

    def _cmd_map(self, args: List[str]) -> bool:
        print(self.display.render_map())
        return True

    def _cmd_tick(self, args: List[str]) -> bool:
        count = self.inputs.parse_tick_count(args)
        for _ in range(count):
            self.system.tick()
        print(f"Advanced {count} tick(s). Current tick: {globalvar.current_tick()}")
        return False

    def _cmd_save(self, args: List[str]) -> bool:
        path = args[0] if args else DEFAULT_SAVE_FILE
        saved = self.system.save_state(path)
        print(f"State saved to {saved}")
        return False

    def _cmd_history(self, args: List[str]) -> bool:
        if not self.inputs.history:
            print("No command history.")
        for index, entry in enumerate(self.inputs.history, start=1):
            print(f"{index:>4}  {entry}")
        return False

    def _cmd_help(self, args: List[str]) -> bool:
        print(HELP_TEXT)
        return False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Run the interactive loop until quit or end of input."""
        print(BANNER)
        while globalvar.get_value("running", True):
            line = self.inputs.read_line("dispatch> ")
            if line is None:
                print("Goodbye.")
                self.system.stop()
                break
            try:
                command, args = self.inputs.parse_command(line)
            except InputError as exc:
                print(f"Error: {exc}")
                continue
            if not command:
                continue
            if command == "quit":
                print("Goodbye.")
                self.system.stop()
                break
            handler = self._handlers[command]
            try:
                advance = handler(args)
            except InputError as exc:
                print(f"Error: {exc}")
                continue
            except Exception:  # Error recovery: keep the system state intact.
                logger.exception("Unexpected error while running '%s'", command)
                print("Unexpected internal error; state preserved. See dispatch.log.")
                continue
            if advance:
                self.system.tick()
            for issue in self.system.check_consistency():
                logger.warning(issue)
                print(f"Warning: {issue}")


def main(argv: Any = None) -> int:
    """Configure logging, then run the interactive dispatcher.

    Args:
        argv: Unused; reserved for future command-line options.

    Returns:
        Process exit code.
    """
    try:
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    except OSError:
        logging.basicConfig(level=logging.WARNING)
    try:
        app = DispatchApp()
    except Exception:
        logger.exception("Failed to initialise the system")
        print("Fatal: could not initialise the system.")
        return 1
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
