"""Command-line interface: parsing, validation and command dispatch.

Commands:
    start [rx ry cx cy]  submit an order (prompts when no arguments given)
    status               system funds, riders and their orders
    orders               all orders with timing and assignment data
    riders               full status-change log for all riders
    map                  current ASCII map
    wait [n]             advance the simulation by n ticks (default 1)
    save [path]          save state to a JSON file
    history              list previous commands
    help                 show this help
    quit / exit          leave the simulator

Shortcuts: s, st, o, r, m, w, h/?, q, x, '!!' (repeat last), '!n' (run
history entry n). After every command the simulation advances one tick.
"""

import logging
from typing import Callable, List, Optional, Sequence

import globalvar
from display import DisplayManager
from path_planner import MAP_SIZE

try:  # readline gives arrow-key history on supported platforms
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

PROMPT = "dispatch> "
WELCOME = ("Food Delivery Dispatch Simulator. "
           "Type 'help' for the command list.")
HELP_TEXT = """Commands:
  start [rx ry cx cy]  submit order (restaurant then customer, 0-800)
  status               funds, riders and order lists
  orders               order table with timing and riders
  riders               rider status-change log
  map                  ASCII map (R rider, S restaurant, C customer)
  wait [n]             advance n ticks (default 1)
  save [path]          save state to JSON (default dispatch_state.json)
  history              show command history
  help                 show this help
  quit | exit          leave the program
Shortcuts: s st o r m w h ? q x  |  !! repeat last  |  !n run history n
Each command advances the simulation by one tick."""

logger = logging.getLogger("dispatch.input")


class InputManager:
    """Parses user commands, validates input and runs the simulator loop."""

    def __init__(self, system_manager, display: DisplayManager,
                 input_func: Callable[[str], str] = input,
                 output_func: Callable[[str], None] = print) -> None:
        """Create the CLI.

        Args:
            system_manager: SystemManager instance managing the simulation.
            display: DisplayManager used for all output rendering.
            input_func: Function used to read a line (injectable for tests).
            output_func: Function used to print output.
        """
        self.system = system_manager
        self.display = display
        self.input_func = input_func
        self.output_func = output_func
        self.history: List[str] = []
        self.aliases = {
            "s": "start", "st": "status", "o": "orders", "r": "riders",
            "m": "map", "w": "wait", "h": "help", "?": "help",
            "q": "quit", "x": "exit",
        }

    # ----- validation ----------------------------------------------------
    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Parse and validate four integer coordinates.

        Accepts space- or comma-separated values.

        Args:
            tokens: Raw argument strings.

        Returns:
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: On wrong count, non-integer input or out-of-range
                values.
        """
        parts: List[str] = []
        for token in tokens:
            parts.extend(token.replace(",", " ").split())
        if len(parts) != 4:
            raise ValueError(
                "Expected 4 integers: restaurant_x restaurant_y "
                f"customer_x customer_y (got {len(parts)})")
        values: List[int] = []
        for part in parts:
            try:
                value = int(part)
            except ValueError:
                raise ValueError(f"'{part}' is not an integer") from None
            if not 0 <= value <= MAP_SIZE:
                raise ValueError(
                    f"Coordinate {value} is out of range 0-{MAP_SIZE}")
            values.append(value)
        return values

    # ----- main loop -----------------------------------------------------
    def run(self) -> None:
        """Run the main loop: one command and one tick per iteration."""
        self._print(WELCOME)
        while globalvar.get_value("running", True):
            try:
                line = self.input_func(PROMPT)
            except EOFError:
                self._print("")
                globalvar.set_value("running", False)
                break
            except KeyboardInterrupt:
                self._print("\nUse 'quit' or 'exit' to leave the simulator.")
                continue

            line = (line or "").strip()
            if not line:
                continue
            command_line = self._resolve_history(line)
            if command_line is None:
                continue
            self.history.append(command_line)

            try:
                self.dispatch(command_line)
            except Exception as exc:
                logger.exception("Command failed: %s", command_line)
                self._print(f"Error: could not run '{command_line}': {exc}")

            if globalvar.get_value("running", True):
                self._advance_tick()

    def _advance_tick(self) -> None:
        """Advance the simulation by one tick, recovering from errors."""
        try:
            self.system.tick()
        except Exception:
            logger.exception("Simulation tick failed")
            self._print("Warning: simulation tick failed; see log for details.")

    def _resolve_history(self, line: str) -> Optional[str]:
        """Expand '!!' and '!n' history references."""
        if line == "!!":
            if not self.history:
                self._print("No previous command.")
                return None
            return self.history[-1]
        if line.startswith("!") and line[1:].isdigit():
            index = int(line[1:])
            if 1 <= index <= len(self.history):
                return self.history[index - 1]
            self._print(f"No history entry {index}.")
            return None
        return line

    def dispatch(self, line: str) -> None:
        """Parse one command line and run the matching handler.

        Args:
            line: Command text entered by the user.
        """
        tokens = line.split()
        command = tokens[0].lower()
        command = self.aliases.get(command, command)
        args = tokens[1:]
        handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "wait": self.cmd_wait,
            "save": self.cmd_save,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }
        handler = handlers.get(command)
        if handler is None:
            self._print(f"Unknown command '{tokens[0]}'. Type 'help'.")
            return
        handler(args)

    # ----- command handlers ----------------------------------------------
    def cmd_start(self, args: Sequence[str]) -> None:
        """Submit an order: ``start rx ry cx cy`` or prompted input."""
        if not args:
            try:
                args = [self.input_func(
                    "Enter restaurant_x restaurant_y customer_x customer_y: ")]
            except EOFError:
                globalvar.set_value("running", False)
                return
        try:
            coords = self.parse_coordinates(args)
        except ValueError as exc:
            self._print(f"Input error: {exc}")
            return
        restaurant = (coords[0], coords[1])
        customer = (coords[2], coords[3])
        try:
            result = self.system.submit_order(restaurant, customer)
        except (ValueError, TypeError) as exc:
            self._print(f"Order rejected: {exc}")
            return
        self._print(self.display.render_assignment(
            result["rider"], result["order"], result["new_rider"]))

    def cmd_status(self, args: Sequence[str]) -> None:
        """Show the status snapshot."""
        self._print(self.display.render_status())

    def cmd_orders(self, args: Sequence[str]) -> None:
        """Show the order table."""
        self._print(self.display.render_orders())

    def cmd_riders(self, args: Sequence[str]) -> None:
        """Show the rider status-change log."""
        self._print(self.display.render_rider_log())

    def cmd_map(self, args: Sequence[str]) -> None:
        """Show the ASCII map."""
        self._print(self.display.render_map())

    def cmd_wait(self, args: Sequence[str]) -> None:
        """Advance the simulation by ``n`` ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                self._print(f"'{args[0]}' is not an integer.")
                return
            if not 1 <= count <= 1000:
                self._print("Number of ticks must be between 1 and 1000.")
                return
        for _ in range(count):
            self._advance_tick()
        self._print(f"Advanced {count} tick(s); now at tick "
                    f"{globalvar.get_value('tick', 0)}.")

    def cmd_save(self, args: Sequence[str]) -> None:
        """Save the current state to a JSON file."""
        path = args[0] if args else "dispatch_state.json"
        try:
            self.system.save_state(path)
            self._print(f"State saved to {path}.")
        except OSError as exc:
            self._print(f"Could not save state: {exc}")

    def cmd_history(self, args: Sequence[str]) -> None:
        """List previously entered commands."""
        if not self.history:
            self._print("History is empty.")
            return
        for index, entry in enumerate(self.history, start=1):
            self._print(f"{index:>4}  {entry}")

    def cmd_help(self, args: Sequence[str]) -> None:
        """Show the command help."""
        self._print(HELP_TEXT)

    def cmd_quit(self, args: Sequence[str]) -> None:
        """Stop the main loop."""
        globalvar.set_value("running", False)
        self._print("Goodbye.")

    def _print(self, text: str) -> None:
        """Write text through the configured output function."""
        self.output_func(text)
