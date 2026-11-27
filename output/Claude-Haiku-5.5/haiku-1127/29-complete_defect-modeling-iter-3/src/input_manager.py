"""Command parsing, input validation and the interactive command loop."""

import logging
from typing import Callable, Dict, List, Sequence, Tuple

from display import DisplayManager
from order_model import STATUS_COMPLETED
from path_planner import MAP_SIZE, PathPlanner

try:  # Enables line editing and history on platforms that support it.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows without pyreadline
    readline = None

logger = logging.getLogger(__name__)

ALIASES: Dict[str, str] = {
    "s": "start", "start": "start",
    "st": "status", "status": "status",
    "o": "orders", "orders": "orders",
    "r": "riders", "riders": "riders",
    "m": "map", "map": "map",
    "t": "tick", "tick": "tick",
    "hist": "history", "history": "history",
    "h": "help", "help": "help", "?": "help",
    "q": "quit", "quit": "quit", "exit": "quit",
}

HELP_TEXT = """Commands:
  start  (s)            Enter: restaurant_x restaurant_y customer_x customer_y (0-800)
  status (st)           System funds, riders and active orders
  orders (o)            Details of all orders
  riders (r)            Status-change log of every rider
  map    (m)            ASCII map of riders, restaurants, customers and streets
  tick   (t) [n]        Advance the simulation by n ticks (default 1)
  history (hist)        Show command history
  !!                    Repeat the previous command
  help   (h, ?)         Show this help
  quit   (q, exit)      Exit the program"""


def parse_coordinates(tokens: Sequence[str]) -> Tuple[int, int, int, int]:
    """Parse and validate four integer coordinates.

    Args:
        tokens: Exactly four string tokens.

    Returns:
        Tuple ``(restaurant_x, restaurant_y, customer_x, customer_y)``.

    Raises:
        ValueError: If the count, type or range is wrong.
    """
    if len(tokens) != 4:
        raise ValueError(f"expected 4 integers, got {len(tokens)}")
    values: List[int] = []
    for token in tokens:
        try:
            value = int(token)
        except ValueError as exc:
            raise ValueError(f"'{token}' is not an integer") from exc
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"coordinate {value} is out of range 0-{MAP_SIZE}")
        values.append(value)
    return values[0], values[1], values[2], values[3]


def _cell_text(point: Tuple[int, int]) -> str:
    """Describe a point as grid cell (col,row) and its centre."""
    col = PathPlanner.to_cell_index(point[0])
    row = PathPlanner.to_cell_index(point[1])
    return f"cell (col {col}, row {row}) centre {PathPlanner.cell_center_point(point)}"


class InputManager:
    """Reads user commands, dispatches them to the system and prints results."""

    def __init__(self, system) -> None:
        """Create the command interface.

        Args:
            system: The :class:`system.SystemManager` to control.
        """
        self.system = system
        self.display = DisplayManager()
        self.command_history: List[str] = []
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "tick": self._cmd_tick,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
        }

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Run the interactive loop until the user quits."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            self.handle_line(line)

    def handle_line(self, line: str) -> None:
        """Process one line of user input with error recovery.

        Args:
            line: Raw input line.
        """
        text = line.strip()
        if not text:
            return
        if text == "!!":
            if not self.command_history:
                print("No previous command.")
                return
            text = self.command_history[-1]
            print(f"Repeating: {text}")
        self.command_history.append(text)
        try:
            self.dispatch(text)
        except ValueError as exc:
            print(f"Input error: {exc}")
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            logger.exception("Command failed: %s", text)
            print(f"Unexpected error: {exc}. The system state has been preserved.")

    def dispatch(self, text: str) -> None:
        """Parse a command line and invoke its handler.

        Args:
            text: Command text.

        Raises:
            ValueError: If the command is unknown.
        """
        tokens = text.replace(",", " ").split()
        name = ALIASES.get(tokens[0].lower())
        if name is None:
            raise ValueError(f"unknown command '{tokens[0]}'. Type 'help' for commands.")
        self._handlers[name](tokens[1:])

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _cmd_start(self, args: List[str]) -> None:
        """Create and dispatch an order, then run it to completion."""
        if not args:
            prompt = "Enter restaurant_x restaurant_y customer_x customer_y (0-800): "
            args = input(prompt).replace(",", " ").split()
        rx, ry, cx, cy = parse_coordinates(args)
        result = self.system.submit_order((rx, ry), (cx, cy))
        order = result["order"]
        rider = result["rider"]

        print(f"Order #{order.id} created at tick {order.start_time}")
        print(f"Restaurant: {_cell_text(order.res_center)}")
        print(f"Customer:   {_cell_text(order.cus_center)}")
        print(f"New rider added: {'yes' if result['new_rider'] else 'no'}")
        if rider is None:
            print("No rider available. The order is pending and will be assigned "
                  "when a rider becomes free.")
            return
        print(f"Assigned rider {rider.rider_id} (speed {rider.speed} units/tick)")
        route = result["route"]
        print(self.display.render_route_graph(
            route, order.res_center, order.cus_center, (rider.x, rider.y)))
        print(f"Route distance: {route.total_distance} units, "
              f"estimated time: {result['estimated_ticks']} tick(s)")
        self.system.run_until_complete(order)
        if order.status == STATUS_COMPLETED:
            print(f"Delivered at tick {order.completion_time}; time taken "
                  f"{order.time_taken} tick(s); efficiency {order.efficiency} units/tick")
        else:
            print("Delivery did not finish within the tick limit; check 'orders'.")

    def _cmd_status(self, args: List[str]) -> None:
        """Print the system snapshot."""
        print(self.display.render_status(
            self.system.funds, self.system.riders, self.system.order_manager.orders))

    def _cmd_orders(self, args: List[str]) -> None:
        """Print details of all orders."""
        print(self.display.render_orders(self.system.order_manager.orders))

    def _cmd_riders(self, args: List[str]) -> None:
        """Print the status-change log of all riders."""
        print(self.display.render_rider_logs(self.system.riders))

    def _cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map."""
        print(self.display.render_map(self.system.riders, self.system.order_manager.orders))

    def _cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError as exc:
                raise ValueError(f"'{args[0]}' is not an integer") from exc
        if not 1 <= count <= 10000:
            raise ValueError("tick count must be between 1 and 10000")
        for _ in range(count):
            self.system.tick()
        print(f"Advanced {count} tick(s); current tick {self.system.current_tick}")

    def _cmd_history(self, args: List[str]) -> None:
        """Print the command history."""
        if not self.command_history:
            print("History is empty.")
            return
        for idx, cmd in enumerate(self.command_history, start=1):
            print(f"{idx:>4}  {cmd}")

    def _cmd_help(self, args: List[str]) -> None:
        """Print the help text."""
        print(HELP_TEXT)

    def _cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.is_running = False
        print("Goodbye.")
