"""Command parsing, input validation and command dispatch for the CLI."""

import logging
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from display_manager import DisplayManager
from order_model import INPUT_MAX, INPUT_MIN
from path_planner import PathPlanner
from system import SystemManager

logger = logging.getLogger(__name__)

SHORTCUTS: Dict[str, str] = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "t": "tick",
    "m": "map",
    "h": "help",
    "?": "help",
    "sv": "save",
    "hist": "history",
    "q": "quit",
    "x": "exit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant x y, customer x y; 0-1000)
                       and show the assigned rider's route.
  status               System funds, riders and their orders.
  orders               Details for all orders.
  riders               Status change log of all riders.
  tick [n]             Advance the simulation by n ticks (default 1).
  map                  Show the ASCII map with riders and orders.
  save [file]          Save the system state as JSON (default dispatch_state.json).
  history              Show the command history.
  !! / !n              Repeat the last command / the n-th history entry.
  help (h, ?)          Show this help.
  quit (q) / exit (x)  Leave the program.
Shortcuts: s=start, st=status, o=orders, r=riders, t=tick, m=map, sv=save"""


class InputManager:
    """Parses and executes user commands.

    Attributes:
        system (SystemManager): The simulation being controlled.
        display (DisplayManager): Formatter for output text.
        reader (Callable[[str], str]): Function used to prompt for input.
        command_history (list[str]): Previously entered commands.
    """

    def __init__(self, system: SystemManager,
                 display: Optional[DisplayManager] = None,
                 reader: Callable[[str], str] = input) -> None:
        """Create the input manager.

        Args:
            system: The SystemManager to control.
            display: Optional display manager; a default one is created if None.
            reader: Function used to read additional input lines.
        """
        self.system = system
        self.display = display or DisplayManager()
        self.planner = PathPlanner()
        self.reader = reader
        self.command_history: List[str] = []
        self._commands: Dict[str, Callable[[List[str]], str]] = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "tick": self.cmd_tick,
            "map": self.cmd_map,
            "save": self.cmd_save,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    @staticmethod
    def parse_command(line: str) -> Tuple[str, List[str]]:
        """Split a line into a command name and arguments.

        Shortcut keys are expanded to full command names.

        Args:
            line: Raw input line.

        Returns:
            Tuple ``(command, arguments)``; command is '' for blank input.
        """
        tokens = line.strip().split()
        if not tokens:
            return "", []
        name = tokens[0].lower()
        return SHORTCUTS.get(name, name), tokens[1:]

    @staticmethod
    def parse_coordinates(tokens: Sequence[str]) -> List[int]:
        """Validate and convert four coordinate tokens.

        Args:
            tokens: Four strings: restaurant x, restaurant y, customer x,
                customer y.

        Returns:
            List of four integers.

        Raises:
            ValueError: On wrong count, non-integer or out-of-range values.
        """
        if len(tokens) != 4:
            raise ValueError(
                "expected 4 integer coordinates: restaurant_x restaurant_y "
                "customer_x customer_y"
            )
        values: List[int] = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise ValueError(f"'{token}' is not an integer") from None
            if not INPUT_MIN <= value <= INPUT_MAX:
                raise ValueError(
                    f"coordinate {value} is out of range {INPUT_MIN}-{INPUT_MAX}"
                )
            values.append(value)
        return values

    def _expand_history(self, line: str) -> Optional[str]:
        """Resolve '!!' and '!n' history references.

        Args:
            line: Stripped input line.

        Returns:
            The expanded command, or None when the reference is invalid.
        """
        if line == "!!":
            return self.command_history[-1] if self.command_history else None
        if line.startswith("!") and line[1:].isdigit():
            index = int(line[1:])
            if 1 <= index <= len(self.command_history):
                return self.command_history[index - 1]
            return None
        return line

    def handle(self, line: str) -> str:
        """Execute one input line and return the text to print.

        Args:
            line: Raw input line.

        Returns:
            Output text (may be empty). Errors are reported as text.
        """
        stripped = line.strip()
        if not stripped:
            return ""
        expanded = self._expand_history(stripped)
        if expanded is None:
            return "No matching command in history."
        self.command_history.append(expanded)
        command, args = self.parse_command(expanded)
        handler = self._commands.get(command)
        if handler is None:
            return f"Unknown command '{command}'. Type 'help' for the command list."
        try:
            return handler(args)
        except ValueError as exc:
            return f"Input error: {exc}"
        except Exception as exc:  # error recovery: keep the system running
            logger.exception("Command '%s' failed", command)
            return f"Internal error: {exc}. System state was preserved."

    def cmd_start(self, args: List[str]) -> str:
        """Create an order and show the assigned rider's route.

        Args:
            args: Four coordinates, or empty to be prompted for them.
        """
        if not args:
            args = self.reader(
                "Enter restaurant_x restaurant_y customer_x customer_y: "
            ).split()
        values = self.parse_coordinates(args)
        res_pos = (values[0], values[1])
        cus_pos = (values[2], values[3])
        result = self.system.submit_order(res_pos, cus_pos)
        order = result["order"]
        rider = result["rider"]

        lines = [
            f"Order #{order.id} created at t={order.start_time}.",
            f"Restaurant grid point: ({order.restaurant_x}, {order.restaurant_y})",
            f"Customer grid point: ({order.customer_x}, {order.customer_y})",
            f"New rider added: {'yes' if result['new_rider'] else 'no'}",
        ]
        if rider is None:
            lines.append(
                f"No rider available; order is pending (funds: {self.system.funds})."
            )
            return "\n".join(lines)

        lines.append(f"Assigned to Rider #{rider.rider_id} "
                     f"(state: {self._state_name(rider)}, "
                     f"active orders: {len(rider.active_orders())}).")
        route = self.planner.route_through(
            [rider.position(), order.restaurant_pos, order.customer_pos]
        )
        lines.append(self.display.render_map(
            riders=self.system.riders, orders=[order], route=route))
        lines.append(self.display.format_route_summary(order, rider, self.planner))
        return "\n".join(lines)

    @staticmethod
    def _state_name(rider) -> str:
        """Return a readable state name for a rider."""
        from rider import STATE_NAMES
        return STATE_NAMES[rider.state]

    def cmd_status(self, args: List[str]) -> str:
        """Show the system status snapshot."""
        return self.display.format_status(self.system)

    def cmd_orders(self, args: List[str]) -> str:
        """Show the details of all orders."""
        return self.display.format_orders(self.system.order_manager.orders)

    def cmd_riders(self, args: List[str]) -> str:
        """Show the status change log of all riders."""
        return self.display.format_rider_logs(self.system.riders)

    def cmd_tick(self, args: List[str]) -> str:
        """Advance the simulation.

        Args:
            args: Optional number of ticks.
        """
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"'{args[0]}' is not an integer tick count") from None
        events = self.system.run_ticks(count)
        lines = [f"Advanced {count} tick(s). Current time: t={self.system.simulated_time}."]
        if events:
            lines.extend(self.display.format_event(entry) for entry in events)
        else:
            lines.append("No rider status changes.")
        lines.append(f"System funds: {self.system.funds}")
        return "\n".join(lines)

    def cmd_map(self, args: List[str]) -> str:
        """Show the ASCII map with riders and active orders."""
        active = [o for o in self.system.order_manager.orders if o.status != "completed"]
        return self.display.render_map(riders=self.system.riders, orders=active)

    def cmd_save(self, args: List[str]) -> str:
        """Save the system state to a JSON file.

        Args:
            args: Optional file path.
        """
        path = args[0] if args else "dispatch_state.json"
        try:
            self.system.save_state(path)
        except OSError as exc:
            return f"Could not save state to {path}: {exc}"
        return f"State saved to {path}."

    def cmd_history(self, args: List[str]) -> str:
        """Show the command history."""
        if not self.command_history:
            return "No commands entered yet."
        return "\n".join(f"{i:>3}  {cmd}" for i, cmd in enumerate(self.command_history, 1))

    def cmd_help(self, args: List[str]) -> str:
        """Show the command help text."""
        return HELP_TEXT

    def cmd_quit(self, args: List[str]) -> str:
        """Stop the main loop."""
        self.system.is_running = False
        return "Goodbye."
