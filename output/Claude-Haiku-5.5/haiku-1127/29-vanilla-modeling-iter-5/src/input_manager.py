"""Command parsing, validation and the interactive command loop.

Commands:
    start [rx ry cx cy]   create an order and run it to completion
    status                system snapshot
    orders                order table
    riders                rider status-change history
    map                   ASCII map
    tick [n]              advance the simulation by n ticks
    save [path]           write a JSON snapshot
    history               list previous commands
    help                  show help
    quit / exit           leave the program

Shortcuts: s=start, st=status, o=orders, r=riders, m=map, t=tick,
sv=save, h or ?=help, q/e=quit/exit, !!=repeat last, !n=repeat history entry n.
"""

import logging
from typing import Dict, List, Optional, Callable

import config
from display import DisplayManager
from grid import MAP_SIZE
from order_model import STATUS_COMPLETED, STATUS_PENDING
from rider import Rider

try:  # enables arrow-key editing and history on platforms that support it
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows without pyreadline
    readline = None

logger = logging.getLogger(__name__)

ALIASES: Dict[str, str] = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "sv": "save",
    "h": "help",
    "?": "help",
    "q": "quit",
    "e": "exit",
}

MAX_TICK_BATCH = 10000

HELP_TEXT = """Commands:
  start [rx ry cx cy]  order from restaurant (rx, ry) to customer (cx, cy), 0-800
  status               system funds, riders and their orders
  orders               all orders with times, distance and rider
  riders               rider status-change history
  map                  ASCII map (R rider, S restaurant, C customer, # street)
  tick [n]             advance simulation by n ticks (default 1)
  save [path]          save a JSON snapshot
  history              show command history
  help                 show this help
  quit | exit          leave the program
Shortcuts: s, st, o, r, m, t, sv, h, ?, q, e, !!, !n"""


def parse_coordinates(tokens: List[str]) -> List[int]:
    """Convert four tokens into validated integer coordinates.

    Args:
        tokens: Raw string tokens.

    Returns:
        List of four integers.

    Raises:
        ValueError: If a token is not an integer or is outside 0-800.
    """
    if len(tokens) != 4:
        raise ValueError("expected 4 coordinates: restaurant_x restaurant_y customer_x customer_y")
    values: List[int] = []
    for token in tokens:
        try:
            value = int(token)
        except ValueError:
            raise ValueError(f"'{token}' is not an integer") from None
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"{value} is outside the allowed range 0-{MAP_SIZE}")
        values.append(value)
    return values


class InputManager:
    """Reads commands from standard input and dispatches them.

    Attributes:
        system: The SystemManager being driven.
        display: The DisplayManager used for output.
        command_history: Executed command lines, oldest first.
    """

    def __init__(self, system, display: Optional[DisplayManager] = None) -> None:
        """Create the input manager.

        Args:
            system: SystemManager instance.
            display: Optional DisplayManager; one is created otherwise.
        """
        self.system = system
        self.display = display if display is not None else DisplayManager(system)
        self.command_history: List[str] = []
        self._handlers: Dict[str, Callable[[List[str]], None]] = {
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
        """Run the interactive main loop until the system stops."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            try:
                self.handle_line(line)
            except Exception:  # error recovery: report and continue
                logger.exception("command failed")
                print("An unexpected error occurred; the system state was preserved.")
        print("Goodbye.")

    def handle_line(self, line: str) -> None:
        """Parse and execute one command line.

        Args:
            line: Raw user input.
        """
        line = line.strip()
        if not line:
            return
        if line == "!!":
            if not self.command_history:
                print("No previous command.")
                return
            line = self.command_history[-1]
        elif line.startswith("!") and line[1:].isdigit():
            index = int(line[1:])
            if not 1 <= index <= len(self.command_history):
                print(f"No history entry {index}.")
                return
            line = self.command_history[index - 1]

        self.command_history.append(line)
        tokens = line.split()
        name = tokens[0].lower()
        command = ALIASES.get(name, name)
        handler = self._handlers.get(command)
        if handler is None:
            print(f"Unknown command '{tokens[0]}'. Type 'help' for a list of commands.")
            return
        handler(tokens[1:])

    def cmd_start(self, args: List[str]) -> None:
        """Create an order and simulate until it is delivered.

        Args:
            args: Four coordinate tokens, or none to be prompted.
        """
        if not args:
            args = input("Enter restaurant_x restaurant_y customer_x customer_y: ").split()
        try:
            coords = parse_coordinates(args)
        except ValueError as exc:
            print(f"Invalid input: {exc}")
            return

        riders_before = len(self.system.riders)
        order = self.system.submit_order((coords[0], coords[1]), (coords[2], coords[3]))
        new_riders = len(self.system.riders) - riders_before
        if order.status == STATUS_PENDING:
            print(
                f"Order #{order.id} queued: no rider available "
                f"(funds: {self.system.funds}). Use 'tick' to advance time."
            )
            return

        rider = self.system.find_rider(order.rider_id)
        trail = [(rider.x, rider.y)] if rider is not None else []
        limit = int(config.CONFIG["max_ticks_per_order"])
        ticks = 0
        while order.status != STATUS_COMPLETED and ticks < limit:
            self.system.tick()
            ticks += 1
            rider = self.system.find_rider(order.rider_id)
            if rider is not None:
                trail.append((rider.x, rider.y))

        if order.status != STATUS_COMPLETED:
            print(f"Order #{order.id} not completed within {limit} ticks.")
            print(self.display.render_map(trail))
            return
        print(self.display.render_route_map(order, trail, rider, new_riders))

    def cmd_status(self, args: List[str]) -> None:
        """Print the system snapshot.

        Args:
            args: Ignored.
        """
        print(self.display.render_status())

    def cmd_orders(self, args: List[str]) -> None:
        """Print the order table.

        Args:
            args: Ignored.
        """
        print(self.display.render_orders())

    def cmd_riders(self, args: List[str]) -> None:
        """Print each rider's status-change history.

        Args:
            args: Ignored.
        """
        print(self.display.render_rider_log())

    def cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map.

        Args:
            args: Ignored.
        """
        print(self.display.render_map())

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation.

        Args:
            args: Optional number of ticks.
        """
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                print(f"'{args[0]}' is not an integer.")
                return
            if not 1 <= count <= MAX_TICK_BATCH:
                print(f"Tick count must be between 1 and {MAX_TICK_BATCH}.")
                return
        for _ in range(count):
            self.system.tick()
        completed = len(self.system.order_manager.completed_orders())
        print(
            f"Advanced {count} tick(s). Current tick: {self.system.current_tick}. "
            f"Completed orders: {completed}. Funds: {self.system.funds}."
        )

    def cmd_save(self, args: List[str]) -> None:
        """Save a JSON snapshot.

        Args:
            args: Optional destination path.
        """
        try:
            path = self.system.save_state(args[0] if args else None)
        except OSError as exc:
            print(f"Could not save state: {exc}")
            return
        print(f"State saved to {path}.")

    def cmd_history(self, args: List[str]) -> None:
        """Print the command history.

        Args:
            args: Ignored.
        """
        if not self.command_history:
            print("No commands yet.")
            return
        for index, entry in enumerate(self.command_history, start=1):
            print(f"{index:>4}  {entry}")

    def cmd_help(self, args: List[str]) -> None:
        """Print help text.

        Args:
            args: Ignored.
        """
        print(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop.

        Args:
            args: Ignored.
        """
        self.system.shutdown()
