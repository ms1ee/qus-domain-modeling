"""Command-line interface: parsing, validation, history and dispatch."""

import logging
import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import storage
from display import DisplayManager
from grid_map import MAP_SIZE

logger = logging.getLogger(__name__)

DEFAULT_SAVE_FILE = "dispatch_state.json"
MAX_TICKS_PER_COMMAND = 10000

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
    "hist": "history",
}

BANNER = (
    "Food Delivery Order Dispatch System\n"
    "Type 'help' for commands. Shortcuts: s=start st=status o=orders "
    "r=riders m=map t=tick h=help q=quit, '!!' repeats the last command."
)

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant then customer, 0-800)
  status               Funds, riders and their current state
  orders               All orders with timing and rider data
  riders               Full status-change log for every rider
  map                  ASCII city map (R rider, S restaurant, C customer)
  tick [n]             Advance simulated time by n ticks (default 1)
  save [file]          Save state to JSON (default dispatch_state.json)
  history              Show command history
  help                 Show this help
  quit / exit          Leave the program
Shortcuts: s st o r m t h ? q x hist, and !! for the previous command."""


def parse_coordinates(tokens: Sequence[str]) -> Tuple[int, int, int, int]:
    """Validate four integer coordinates.

    Args:
        tokens: Exactly four strings ``rx ry cx cy``.

    Returns:
        Tuple of four integers.

    Raises:
        ValueError: If the count, type or range is wrong.
    """
    if len(tokens) != 4:
        raise ValueError("expected 4 coordinates: restaurant_x restaurant_y customer_x customer_y")
    values: List[int] = []
    for token in tokens:
        try:
            values.append(int(token))
        except ValueError:
            raise ValueError(f"'{token}' is not an integer")
    for value in values:
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"coordinate {value} is out of range 0-{MAP_SIZE}")
    return values[0], values[1], values[2], values[3]


class InputManager:
    """Reads commands from the user and dispatches them to handlers."""

    def __init__(
        self,
        system,
        display: DisplayManager,
        input_func: Callable[[str], str] = input,
        output_func: Callable[..., None] = print,
    ) -> None:
        """Create the input manager.

        Args:
            system: The SystemManager controlling the simulation.
            display: Renderer for all textual output.
            input_func: Function used to read a line (injectable for tests).
            output_func: Function used to print output.
        """
        self.system = system
        self.display = display
        self.input_func = input_func
        self.output_func = output_func
        self.command_history: List[str] = []
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
            "exit": self._cmd_quit,
        }

    def _print(self, text: str = "") -> None:
        self.output_func(text)

    def run(self) -> None:
        """Run the interactive loop until the system stops."""
        self._print(BANNER)
        while self.system.is_running:
            try:
                line = self.input_func("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self._print()
                self.system.stop()
                break
            try:
                self.execute(line)
            except Exception as exc:  # error recovery: report and continue
                logger.exception("command failed")
                self._print(f"Error: unexpected failure ({exc}). System state preserved.")

    def execute(self, line: str) -> None:
        """Parse and run a single command line.

        Args:
            line: Raw text entered by the user.
        """
        text = line.strip()
        if not text:
            return
        if text == "!!":
            if not self.command_history:
                self._print("No previous command.")
                return
            text = self.command_history[-1]
            self._print(f"Repeating: {text}")
        self.command_history.append(text)

        tokens = text.split()
        name = tokens[0].lower()
        name = ALIASES.get(name, name)
        handler = self._handlers.get(name)
        if handler is None:
            self._print(f"Unknown command '{tokens[0]}'. Type 'help' for the list of commands.")
            return
        handler(tokens[1:])

    # ----- handlers -----------------------------------------------------
    def _cmd_start(self, args: List[str]) -> None:
        if not self.system.is_running:
            self._print("System is stopped.")
            return
        if not args:
            prompt = self.input_func("Enter restaurant_x restaurant_y customer_x customer_y: ")
            args = prompt.split()
        try:
            rx, ry, cx, cy = parse_coordinates(args)
        except ValueError as exc:
            self._print(f"Input error: {exc}")
            return

        result = self.system.submit_order((rx, ry), (cx, cy))
        order = result["order"]
        rider = result["rider"]
        grid = self.system.order_manager  # keeps reference for clarity
        del grid
        geo = self.display.grid_map

        self._print(f"Order #{order.id} created at t={order.start_time}.")
        self._print(
            f"  Restaurant: input=({rx},{ry}) grid_point={order.restaurant_pos} "
            f"cell={geo.cell_of(order.restaurant_pos)} centre={geo.cell_center(order.restaurant_pos)}"
        )
        self._print(
            f"  Customer:   input=({cx},{cy}) grid_point={order.customer_pos} "
            f"cell={geo.cell_of(order.customer_pos)} centre={geo.cell_center(order.customer_pos)}"
        )
        if result["new_rider"]:
            self._print(f"  New rider added: yes (rider #{rider.rider_id if rider else '?'}, "
                        f"funds now {self.system.funds})")
        else:
            self._print("  New rider added: no")

        if rider is None:
            self._print("  No rider available; the order remains pending.")
            return

        distance = math.sqrt((rider.x - order.restaurant_x) ** 2 + (rider.y - order.restaurant_y) ** 2)
        self._print(
            f"  Assigned to rider #{rider.rider_id} at ({rider.x},{rider.y}), "
            f"{distance:.1f} units from restaurant; state={rider.state_name}"
        )
        planner = self.system.path_planner
        route = planner.route_for_order(rider.position, order.restaurant_pos, order.customer_pos)
        ticks = planner.estimate_ticks(route, rider.speed)
        self._print(self.display.render_route(
            route, rider.speed, ticks, self.system.riders, self.system.order_manager.all_orders()
        ))
        self._print("  The rider begins moving on the next tick (use 'tick').")

    def _cmd_status(self, args: List[str]) -> None:
        self._print(self.display.render_status(self.system))

    def _cmd_orders(self, args: List[str]) -> None:
        self._print(self.display.render_orders(self.system.order_manager.all_orders()))

    def _cmd_riders(self, args: List[str]) -> None:
        self._print(self.display.render_rider_log(self.system.riders))

    def _cmd_map(self, args: List[str]) -> None:
        orders = self.system.order_manager.all_orders()
        self._print(self.display.render_map(self.system.riders, orders))

    def _cmd_tick(self, args: List[str]) -> None:
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                self._print(f"Input error: '{args[0]}' is not an integer")
                return
            if not 1 <= count <= MAX_TICKS_PER_COMMAND:
                self._print(f"Input error: tick count must be 1-{MAX_TICKS_PER_COMMAND}")
                return
        self.system.run_ticks(count)
        self._print(f"Advanced {count} tick(s). Current time: t={self.system.current_time}.")

    def _cmd_save(self, args: List[str]) -> None:
        path = args[0] if args else DEFAULT_SAVE_FILE
        try:
            storage.save_state(path)
            self._print(f"State saved to {path}.")
        except OSError as exc:
            self._print(f"Error: could not save to {path}: {exc}")

    def _cmd_history(self, args: List[str]) -> None:
        if not self.command_history:
            self._print("No commands yet.")
            return
        for index, command in enumerate(self.command_history, start=1):
            self._print(f"  {index:>3}  {command}")

    def _cmd_help(self, args: List[str]) -> None:
        self._print(HELP_TEXT)

    def _cmd_quit(self, args: List[str]) -> None:
        self.system.stop()
        self._print("Goodbye.")
