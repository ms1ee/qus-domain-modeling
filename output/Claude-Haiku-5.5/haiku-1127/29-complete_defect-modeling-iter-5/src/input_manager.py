"""Command parsing, input validation and command dispatch."""

from __future__ import annotations

import logging
import math
from typing import Any, Callable, Dict, List, Optional, Sequence

from config import get_config
from display import DisplayManager
from globalvar import get_value
from path_planner import GridMap, PathPlanner, route_length

logger = logging.getLogger(__name__)

COMMAND_ALIASES = {
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
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant x y, customer x y, 0-800).
                       Prompts for the four values when none are given.
  status               Funds, riders and their current state.
  orders               Details of all orders.
  riders               Chronological log of every rider status change.
  map                  ASCII map with riders, restaurants and customers.
  tick [n]             Advance the simulation by n ticks (default 1).
  history              Show commands entered in this session.
  help                 Show this help text.
  quit / exit          Save state and leave the program.
Shortcuts: s, st, o, r, m, t, h, ?, q, x. Type '!!' to repeat the last command."""


class InputManager:
    """Parses user commands and produces textual responses.

    Attributes:
        system: The SystemManager that executes the commands.
        command_history: Every command line accepted this session.
        display: The DisplayManager used for output formatting.
    """

    def __init__(self, system: Any, input_func: Optional[Callable[[str], str]] = None) -> None:
        """Create the input manager.

        Args:
            system: SystemManager instance.
            input_func: Function used to prompt for extra input (for start).
        """
        self.system = system
        self.command_history: List[str] = []
        self.display = DisplayManager()
        self._input = input_func or input
        self._commands: Dict[str, Callable[[List[str]], str]] = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "tick": self._cmd_tick,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
        }

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Parse and validate four integer coordinates.

        Brackets and commas are accepted as separators, so ``[1,2,3,4]`` works.

        Args:
            tokens: Raw text tokens.

        Returns:
            List of four validated integers.

        Raises:
            ValueError: If the count is wrong, a token is not an integer, or a
                coordinate is outside 0-800.
        """
        cleaned: List[str] = []
        for token in tokens:
            normalized = token.replace("[", " ").replace("]", " ").replace(",", " ")
            cleaned.extend(part for part in normalized.split() if part)
        if len(cleaned) != 4:
            raise ValueError(f"expected 4 integer coordinates, got {len(cleaned)}")
        limit = get_config().map_size
        values: List[int] = []
        for text in cleaned:
            try:
                value = int(text)
            except ValueError:
                raise ValueError(f"'{text}' is not an integer") from None
            if not 0 <= value <= limit:
                raise ValueError(f"coordinate {value} is out of range 0-{limit}")
            values.append(value)
        return values

    def handle(self, line: str) -> str:
        """Execute one command line and return the response text.

        Args:
            line: Raw input line from the user.

        Returns:
            Text to display, possibly empty.
        """
        text = line.strip()
        if not text:
            return ""
        if text == "!!":
            if not self.command_history:
                return "No previous command to repeat."
            text = self.command_history[-1]
        self.command_history.append(text)

        parts = text.split()
        name = COMMAND_ALIASES.get(parts[0].lower(), parts[0].lower())
        handler = self._commands.get(name)
        if handler is None:
            return f"Unknown command '{parts[0]}'. Type 'help' for the command list."
        try:
            return handler(parts[1:])
        except ValueError as exc:
            return f"Input error: {exc}. Try again."

    def _find_rider(self, rider_id: Optional[int]) -> Any:
        """Return the rider with ``rider_id`` or None."""
        for rider in self.system.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def _cmd_start(self, args: List[str]) -> str:
        """Create an order, assign a rider and show the planned route."""
        tokens = list(args)
        if not tokens:
            tokens = self._input(
                "Enter restaurant_x restaurant_y customer_x customer_y (0-800): ").split()
        rx, ry, cx, cy = self.parse_coordinates(tokens)
        order, new_riders = self.system.create_order((rx, ry), (cx, cy))

        lines = [
            f"Order #{order.id} accepted at tick {self.system.current_tick}.",
            f"Restaurant grid point: {order.restaurant_pos}  "
            f"Customer grid point: {order.customer_pos}",
        ]
        if new_riders:
            lines.append("New rider(s) recruited: "
                         + ", ".join(f"#{r.rider_id}" for r in new_riders))
        else:
            lines.append(f"No new rider recruited (funds: {self.system.funds}).")

        rider = self._find_rider(order.rider_id)
        if rider is None:
            lines.append("No rider is available yet; the order is queued as pending.")
            lines.append(self.display.render_map(riders=self.system.riders, orders=[order]))
            return "\n".join(lines)

        start = (rider.x, rider.y)
        waypoints = PathPlanner(GridMap.from_config()).plan_route(
            start, [order.restaurant_pos, order.customer_pos])
        length = route_length(start, waypoints)
        eta = math.ceil(length / rider.speed) if rider.speed > 0 else 0
        lines.append(
            f"Assigned to rider #{rider.rider_id} (speed {rider.speed} units/tick, "
            f"route length {length} units, estimated {eta} tick(s) for this order).")
        queued = len(rider.orders) - 1
        if queued > 0:
            lines.append(f"Note: the rider already has {queued} earlier order(s); "
                         "the estimate excludes them.")
        lines.append(self.display.render_map(
            riders=self.system.riders, orders=[order], route=[start] + waypoints))
        return "\n".join(lines)

    def _cmd_status(self, args: List[str]) -> str:
        """Show the system status snapshot."""
        return self.display.format_status(self.system)

    def _cmd_orders(self, args: List[str]) -> str:
        """Show the details of every order."""
        return self.display.format_orders(get_value("orders") or [])

    def _cmd_riders(self, args: List[str]) -> str:
        """Show the chronological rider status log."""
        return self.display.format_rider_logs(self.system.riders)

    def _cmd_map(self, args: List[str]) -> str:
        """Show the ASCII map with riders and active orders."""
        active = [o for o in get_value("orders") or [] if o.status != "completed"]
        return self.display.render_map(riders=self.system.riders, orders=active)

    def _cmd_tick(self, args: List[str]) -> str:
        """Advance the simulated clock."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError("tick count must be an integer") from None
        limit = get_config().max_tick_batch
        if not 1 <= count <= limit:
            raise ValueError(f"tick count must be between 1 and {limit}")
        self.system.tick(count)
        completed = len(get_value("completed_orders") or [])
        return (f"Advanced {count} tick(s). Now at tick {self.system.current_tick}. "
                f"Funds: {self.system.funds}. Completed orders: {completed}.")

    def _cmd_history(self, args: List[str]) -> str:
        """List the commands entered in this session."""
        if not self.command_history:
            return "No commands entered yet."
        return "\n".join(f"{i:>3}: {cmd}" for i, cmd in enumerate(self.command_history, 1))

    def _cmd_help(self, args: List[str]) -> str:
        """Show the command help text."""
        return HELP_TEXT

    def _cmd_quit(self, args: List[str]) -> str:
        """Stop the main loop."""
        self.system.shutdown()
        return "Shutting down the dispatch system..."
