"""Command parsing, validation, history and command dispatch."""

import logging
import math

from grid import MAP_SIZE, path_length

logger = logging.getLogger("dispatch.input")

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "sv": "save",
    "hist": "history",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]   place an order (prompts for coordinates if omitted)
  status (st)           funds, riders and their orders
  orders (o)            details for all orders
  riders (r)            status-change log for every rider
  map (m)               ASCII map of riders, orders and streets
  tick [n] (t)          advance the simulation by n ticks (default 1)
  save [file]           save system state as JSON
  history (hist)        list command history (recall with !n)
  help (h, ?)           show this help
  quit (q) / exit (x)   leave the program
Each main-loop iteration also advances the simulation by one tick."""


class InputManager:
    """Parses user commands and executes them against the system.

    Attributes:
        system (SystemManager): The simulation being controlled.
        display (DisplayManager): Renderer used for output.
        command_history (list[str]): Previously executed command lines.
    """

    def __init__(self, system, display):
        """Create the input manager.

        Args:
            system: SystemManager instance.
            display: DisplayManager instance.
        """
        self.system = system
        self.display = display
        self.command_history = []
        self._handlers = {
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

    @staticmethod
    def parse_command(text):
        """Split a command line into a canonical command name and arguments.

        Args:
            text: Raw command line.

        Returns:
            tuple: ``(command, args)`` where command is lower-case and aliases
            are resolved. Returns ``("", [])`` for blank input.
        """
        tokens = text.replace(",", " ").split()
        if not tokens:
            return "", []
        command = tokens[0].lower()
        return ALIASES.get(command, command), tokens[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Validate four integer coordinates.

        Args:
            tokens: Sequence of four string tokens.

        Returns:
            list[int]: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the count is wrong, a token is not an integer, or a
                value is outside 0..MAP_SIZE.
        """
        if len(tokens) != 4:
            raise ValueError("expected four integers: restaurant_x restaurant_y "
                             "customer_x customer_y")
        values = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise ValueError(f"'{token}' is not an integer")
            if not 0 <= value <= MAP_SIZE:
                raise ValueError(f"coordinate {value} is out of range 0-{MAP_SIZE}")
            values.append(value)
        return values

    def _recall(self, text):
        """Resolve a ``!n`` history reference to a stored command line.

        Args:
            text: Input beginning with '!'.

        Returns:
            str: The recalled command line.

        Raises:
            ValueError: If the reference is malformed or out of range.
        """
        number = text[1:]
        if not number.isdigit():
            raise ValueError("history reference must look like !<number>")
        index = int(number)
        if not 1 <= index <= len(self.command_history):
            raise ValueError(f"no history entry #{index}")
        return self.command_history[index - 1]

    def execute(self, line):
        """Execute one command line and return the textual output.

        Args:
            line: Raw input line.

        Returns:
            str: Output to display (may be empty). Never raises for user errors.
        """
        text = (line or "").strip()
        if not text:
            return ""
        try:
            if text.startswith("!"):
                text = self._recall(text)
        except ValueError as exc:
            return f"Input error: {exc}"
        self.command_history.append(text)
        command, args = self.parse_command(text)
        handler = self._handlers.get(command)
        if handler is None:
            return f"Unknown command '{command}'. Type 'help' for the command list."
        try:
            return handler(args)
        except ValueError as exc:
            return f"Input error: {exc}"

    def _cmd_start(self, args):
        """Handle ``start``: validate coordinates, create and assign an order.

        Args:
            args: Optional four coordinate tokens; prompts if empty.

        Returns:
            str: Acceptance report including grid points, recruitment info,
            assigned rider, speed, time estimate and the route map.
        """
        if not args:
            args = input("Enter restaurant_x restaurant_y customer_x customer_y (0-800): ")
            args = args.replace(",", " ").split()
        values = self.parse_coordinates(args)
        res_pos = (values[0], values[1])
        cus_pos = (values[2], values[3])
        return self._place_order(res_pos, cus_pos)

    def _place_order(self, res_pos, cus_pos):
        """Create an order, recruit if needed, assign it and build the report.

        Args:
            res_pos: Restaurant input point.
            cus_pos: Customer input point.

        Returns:
            str: Report text.
        """
        system = self.system
        manager = system.order_manager
        order = manager.create_order(res_pos, cus_pos)
        new_rider = None
        if not system.has_idle_rider():
            new_rider = system.recruit_rider()
        rider = manager.assign_order(order)
        if rider is None:
            return (f"Order could not be assigned: no rider available and funds "
                    f"({system.funds}) are insufficient to recruit "
                    f"(cost {system.recruitment_cost}).")
        route = rider.estimate_route(order)
        distance = path_length(route)
        ticks = math.ceil(distance / rider.speed) if rider.speed else 0
        lines = [f"Order #{order.id} accepted.",
                 f"Restaurant grid point: {order.res_pos}   Customer grid point: {order.cus_pos}"]
        if new_rider is not None:
            lines.append(f"New rider added: #{new_rider.rider_id} "
                         f"(cost {system.recruitment_cost}, funds now {system.funds})")
        else:
            lines.append("No new rider added.")
        lines.append(f"Assigned rider: #{rider.rider_id} at ({rider.x}, {rider.y}), "
                     f"speed {rider.speed} units/tick, queued orders: {len(rider.orders)}")
        lines.append(f"Planned route: {distance} units, about {ticks} tick(s) "
                     f"(excluding queued orders)")
        lines.append("Route map (R restaurant, C customer, * route):")
        lines.append(self.display.render_map(system.riders,
                                             system.order_manager.active_orders(), route))
        return "\n".join(lines)

    def _cmd_status(self, args):
        """Handle ``status``."""
        return self.display.render_status(self.system)

    def _cmd_orders(self, args):
        """Handle ``orders``."""
        return self.display.render_orders(self.system.order_manager.orders)

    def _cmd_riders(self, args):
        """Handle ``riders``."""
        return self.display.render_rider_events(self.system.riders)

    def _cmd_map(self, args):
        """Handle ``map``."""
        return self.display.render_map(self.system.riders,
                                       self.system.order_manager.active_orders())

    def _cmd_tick(self, args):
        """Handle ``tick [n]``: advance the simulation by n ticks."""
        steps = 1
        if args:
            if not args[0].isdigit():
                raise ValueError("tick count must be a positive integer")
            steps = int(args[0])
            if not 1 <= steps <= 1000:
                raise ValueError("tick count must be between 1 and 1000")
        self.system.advance_tick(steps)
        return f"Advanced {steps} tick(s). Current tick: {self.system.current_tick}."

    def _cmd_save(self, args):
        """Handle ``save [file]``."""
        try:
            path = self.system.save_state(args[0] if args else None)
        except OSError as exc:
            return f"Could not save state: {exc}"
        return f"State saved to {path}."

    def _cmd_history(self, args):
        """Handle ``history``."""
        if not self.command_history:
            return "History is empty."
        return "\n".join(f"{i:>3}  {cmd}" for i, cmd in enumerate(self.command_history, 1))

    def _cmd_help(self, args):
        """Handle ``help``."""
        return HELP_TEXT

    def _cmd_quit(self, args):
        """Handle ``quit`` and ``exit``: stop the main loop."""
        self.system.is_running = False
        return "Exiting dispatch simulator. Goodbye."
