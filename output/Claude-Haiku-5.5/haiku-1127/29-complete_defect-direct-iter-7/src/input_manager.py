"""Command parsing, input validation and dispatch for the console."""

from __future__ import annotations

import logging
import math
from typing import Callable

import config
from order_model import grid_index
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.input")

COORD_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")

HELP_TEXT = (
    "Commands (every command except help/history/quit advances one tick):\n"
    "  start [rx ry cx cy]  create an order; coordinates are 0-800 and may\n"
    "                       be comma separated; missing values are prompted\n"
    "  status               funds, riders, and each rider's state and orders\n"
    "  orders               details of all orders\n"
    "  riders               status-change log of every rider\n"
    "  map                  ASCII map of riders and active orders\n"
    "  wait [n]             advance n ticks (default 1, max "
    f"{config.MAX_WAIT_COMMAND})\n"
    "  history              list recent commands\n"
    "  !!                   repeat the previous command\n"
    "  !n                   repeat command number n from history\n"
    "  help                 show this help\n"
    "  quit | exit          leave the program\n"
    "Shortcuts: s=start st=status o=orders r=riders m=map w=wait\n"
    "           h=help q=quit x=exit hist=history\n"
)


class CommandError(Exception):
    """A user-facing error in a command."""


class InputManager:
    """Parses console lines, validates them and runs the matching command.

    Each handler returns ``(output_text, ticks)``: the text to print and the
    number of simulation ticks the main loop should advance.
    """

    ALIASES = {
        "s": "start",
        "st": "status",
        "o": "orders",
        "r": "riders",
        "m": "map",
        "w": "wait",
        "h": "help",
        "?": "help",
        "q": "quit",
        "x": "exit",
        "hist": "history",
    }

    def __init__(self, system, display, reader: Callable[[str], str] = input
                 ) -> None:
        """Create the input manager.

        Args:
            system: The SystemManager instance.
            display: The DisplayManager instance.
            reader: Callable used to read prompted values.
        """
        self._system = system
        self._display = display
        self._reader = reader
        self._history: list[str] = []
        self._handlers = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "orders": self._cmd_orders,
            "riders": self._cmd_riders,
            "map": self._cmd_map,
            "wait": self._cmd_wait,
            "history": self._cmd_history,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
        }

    @property
    def history(self) -> list[str]:
        """A copy of the command history (oldest first)."""
        return list(self._history)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def execute(self, line: str) -> tuple[str, int]:
        """Parse and run one console line.

        Args:
            line: Raw text entered by the user.

        Returns:
            tuple[str, int]: Output text and the number of ticks to advance.
        """
        text = (line or "").strip()
        if not text:
            return "", 0
        try:
            if text.startswith("!"):
                text = self._expand_history(text)
            parts = text.split()
            name = parts[0].lower()
            name = self.ALIASES.get(name, name)
            handler = self._handlers.get(name)
            if handler is None:
                raise CommandError(
                    f"unknown command '{parts[0]}'. Type 'help' for commands.")
            self._remember(text)
            return handler(parts[1:])
        except CommandError as exc:
            logger.info("Command rejected: %s (%s)", line, exc)
            return f"Error: {exc}", 0

    def _expand_history(self, text: str) -> str:
        """Resolve '!!' or '!n' shortcuts to a previous command.

        Args:
            text: Shortcut text beginning with '!'.

        Returns:
            str: The expanded command text.

        Raises:
            CommandError: If the reference cannot be resolved.
        """
        if text == "!!":
            if not self._history:
                raise CommandError("there is no previous command")
            return self._history[-1]
        digits = text[1:]
        if digits.isdigit():
            index = int(digits)
            if not 1 <= index <= len(self._history):
                raise CommandError(
                    f"history entry {index} does not exist")
            return self._history[index - 1]
        raise CommandError(f"invalid history reference '{text}'")

    def _remember(self, text: str) -> None:
        """Append a command to the history, bounded by HISTORY_LIMIT."""
        self._history.append(text)
        if len(self._history) > config.HISTORY_LIMIT:
            del self._history[: len(self._history) - config.HISTORY_LIMIT]

    def _prompt(self, message: str) -> str:
        """Read one value through the configured reader."""
        return str(self._reader(message)).strip()

    @staticmethod
    def _parse_coordinate(token: str, label: str) -> int:
        """Validate one coordinate token.

        Args:
            token: Text entered by the user.
            label: Name of the coordinate, used in error messages.

        Returns:
            int: The coordinate.

        Raises:
            CommandError: If the token is not an integer in range.
        """
        try:
            value = int(token)
        except ValueError:
            raise CommandError(f"{label} must be an integer, got '{token}'")
        if not 0 <= value <= config.MAP_SIZE:
            raise CommandError(
                f"{label} {value} is outside the range 0-{config.MAP_SIZE}")
        return value

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _cmd_start(self, args: list[str]) -> tuple[str, int]:
        """Create an order and assign it to a rider."""
        tokens: list[str] = []
        for arg in args:
            tokens.extend(part for part in arg.replace(",", " ").split()
                          if part)
        if len(tokens) > 4:
            raise CommandError("start expects exactly 4 coordinates")

        values = []
        for index, label in enumerate(COORD_LABELS):
            if index < len(tokens):
                token = tokens[index]
            else:
                token = self._prompt(f"Enter {label} (0-{config.MAP_SIZE}): ")
            values.append(self._parse_coordinate(token, label.capitalize()))

        restaurant = (values[0], values[1])
        customer = (values[2], values[3])
        manager = self._system.order_manager
        try:
            order = manager.create_order(restaurant, customer)
        except ValueError as exc:
            raise CommandError(str(exc))

        self._system.add_funds(config.ORDER_FEE)
        new_riders = self._system.check_recruitment()
        rider = manager.assign_order(order)

        rgx, rgy = grid_index(*order.res_pos)
        cgx, cgy = grid_index(*order.cus_pos)
        lines = [
            f"Order #{order.id} created at tick {order.start_tick}.",
            f"Restaurant: input {restaurant} -> grid cell ({rgx},{rgy}), "
            f"centre {order.res_pos}",
            f"Customer:   input {customer} -> grid cell ({cgx},{cgy}), "
            f"centre {order.cus_pos}",
            f"Trip distance: {order.distance} units | "
            f"system funds: {self._system.funds}",
        ]
        if new_riders:
            ids = ", ".join(f"#{r.rider_id}" for r in new_riders)
            lines.append(f"New rider(s) recruited: {ids}")
        if rider is None:
            lines.append("No rider is available; the order is queued and "
                         "will be assigned automatically.")
        else:
            route = PathPlanner.plan_route(rider.position,
                                           [order.res_pos, order.cus_pos])
            length = PathPlanner.route_length(rider.position, route)
            ticks = math.ceil(length / rider.speed)
            lines.append(f"Assigned to rider #{rider.rider_id} "
                         f"(speed {rider.speed} units/tick).")
            lines.append(f"Route length {length} units; estimated time "
                         f"{ticks} tick(s).")
            lines.append(self._display.render_route(
                rider.position, route, order.res_pos, order.cus_pos))
        return "\n".join(lines), 1

    def _cmd_status(self, args: list[str]) -> tuple[str, int]:
        """Show funds, riders and their orders."""
        if args:
            raise CommandError("status takes no arguments")
        return self._display.render_status(self._system), 1

    def _cmd_orders(self, args: list[str]) -> tuple[str, int]:
        """Show details for all orders."""
        if args:
            raise CommandError("orders takes no arguments")
        orders = self._system.order_manager.all_orders()
        return self._display.render_orders(orders), 1

    def _cmd_riders(self, args: list[str]) -> tuple[str, int]:
        """Show every rider's status-change log."""
        if args:
            raise CommandError("riders takes no arguments")
        return self._display.render_rider_log(self._system.riders), 1

    def _cmd_map(self, args: list[str]) -> tuple[str, int]:
        """Show the ASCII city map."""
        if args:
            raise CommandError("map takes no arguments")
        orders = self._system.order_manager.all_orders()
        return self._display.render_map(self._system.riders, orders), 1

    def _cmd_wait(self, args: list[str]) -> tuple[str, int]:
        """Advance the simulation by several ticks."""
        if len(args) > 1:
            raise CommandError("wait takes at most one argument")
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise CommandError(f"wait count must be an integer, "
                                   f"got '{args[0]}'")
        if not 1 <= count <= config.MAX_WAIT_COMMAND:
            raise CommandError(
                f"wait count must be between 1 and {config.MAX_WAIT_COMMAND}")
        return f"Advancing {count} tick(s).", count

    def _cmd_history(self, args: list[str]) -> tuple[str, int]:
        """List the most recent commands with their numbers."""
        if args:
            raise CommandError("history takes no arguments")
        if not self._history:
            return "No commands in history.", 0
        start = max(0, len(self._history) - 20)
        lines = [f"{i + 1:>4}  {cmd}"
                 for i, cmd in enumerate(self._history)][start:]
        return "\n".join(lines), 0

    def _cmd_help(self, args: list[str]) -> tuple[str, int]:
        """Show the command reference."""
        return HELP_TEXT.rstrip(), 0

    def _cmd_quit(self, args: list[str]) -> tuple[str, int]:
        """Request program termination."""
        self._system.stop()
        return "Goodbye.", 0
