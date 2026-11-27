"""Command parsing, validation, history and the interactive main loop."""

import logging
import re

import globalvar
import grid
from display import DisplayManager
from order import OrderManager
from path_planner import PathPlanner
from system import SystemManager

try:  # Enables arrow-key editing and history where available.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

SHORTCUTS = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "w": "wait",
    "sv": "save",
    "hi": "history",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
}

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy]  [s]  Create an order (restaurant then customer, 0-800)
  status               [st] Show funds, riders and their orders
  orders               [o]  Show all orders
  riders               [r]  Show every rider status change
  map                  [m]  Show the ASCII map
  wait [n]             [w]  Advance the simulation n extra ticks (default 1)
  save [path]          [sv] Save state to a JSON file
  history              [hi] Show command history
  !! / !n                   Repeat the last / n-th command
  help                 [h]  Show this help
  quit | exit          [q]  Leave the program
Every command line advances the simulation by one tick."""

logger = logging.getLogger("dispatch.input")


class InputError(Exception):
    """Raised for malformed user input."""


class InputManager:
    """Parse and execute user commands for the dispatch simulator."""

    def __init__(self, input_func=input, output_func=print):
        """Create the manager.

        Args:
            input_func: Callable used to read a line (default ``input``).
            output_func: Callable used to print text (default ``print``).
        """
        self.history = []
        self._input = input_func
        self._output = output_func
        self.commands = {
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

    @staticmethod
    def parse_coordinates(tokens):
        """Parse four integer coordinates from tokens or a text string.

        Args:
            tokens: List of strings, or a single string. Separators may be
                spaces or commas.

        Returns:
            List of four validated integers.

        Raises:
            InputError: If the count, type or range is wrong.
        """
        text = " ".join(tokens) if isinstance(tokens, (list, tuple)) else tokens
        parts = [p for p in re.split(r"[\s,]+", text.strip()) if p]
        if len(parts) != 4:
            raise InputError(
                f"expected 4 coordinates [restaurant_x restaurant_y "
                f"customer_x customer_y], got {len(parts)}"
            )
        values = []
        for part in parts:
            try:
                value = int(part)
            except ValueError:
                raise InputError(f"'{part}' is not an integer")
            try:
                grid.validate_coordinate(value)
            except grid.CoordinateError as exc:
                raise InputError(str(exc))
            values.append(value)
        return values

    def _expand_history(self, line):
        """Expand '!!' and '!n' references to earlier commands."""
        if line == "!!":
            if not self.history:
                raise InputError("no previous command to repeat")
            return self.history[-1]
        match = re.fullmatch(r"!(\d+)", line)
        if match:
            index = int(match.group(1))
            if not 1 <= index <= len(self.history):
                raise InputError(f"no command number {index} in history")
            return self.history[index - 1]
        return line

    def execute(self, line):
        """Execute one command line and return its textual output.

        Args:
            line: Raw input line.

        Returns:
            Output text (possibly empty).
        """
        line = (line or "").strip()
        if not line:
            return ""
        try:
            line = self._expand_history(line)
        except InputError as exc:
            return f"Input error: {exc}"
        self.history.append(line)
        tokens = line.split()
        name = SHORTCUTS.get(tokens[0].lower(), tokens[0].lower())
        handler = self.commands.get(name)
        if handler is None:
            return f"Unknown command '{tokens[0]}'. Type 'help' for commands."
        try:
            return handler(tokens[1:])
        except EOFError:
            raise
        except InputError as exc:
            return f"Input error: {exc}"
        except LookupError as exc:
            return f"Cannot complete request: {exc}"
        except ValueError as exc:
            return f"Error: {exc}"
        except Exception as exc:  # error recovery: keep the session alive
            logger.exception("unexpected error executing '%s'", line)
            return f"Internal error ({exc}); system state preserved."

    def run(self):
        """Run the interactive main loop until the system stops.

        Each loop iteration reads one command, executes it, and then
        advances the simulation by one tick.
        """
        self._output("Food delivery dispatch simulator. Type 'help' for commands.")
        while SystemManager.is_running():
            try:
                line = self._input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                self._output("")
                SystemManager.shutdown()
                break
            text = self.execute(line)
            if text:
                self._output(text)
            if not SystemManager.is_running():
                break
            SystemManager.tick()

    def cmd_start(self, args):
        """Create an order and assign it to the best rider."""
        if not args:
            args = self._input(
                "Enter restaurant_x restaurant_y customer_x customer_y: "
            ).split()
        coords = self.parse_coordinates(args)
        order = OrderManager.create_order(coords[:2], coords[2:])
        rider, new_rider, eta = OrderManager.assign_order(order)
        route = PathPlanner.plan_multi_route(
            grid.snap_to_grid(rider.x, rider.y),
            [order.res_pos, order.cus_pos],
        )
        recruited = (f"yes (rider #{rider.rider_id})" if new_rider else "no")
        lines = [
            f"Order #{order.id} created and assigned.",
            f"Restaurant: input ({coords[0]}, {coords[1]}) -> grid {order.res_pos}",
            f"Customer:   input ({coords[2]}, {coords[3]}) -> grid {order.cus_pos}",
            f"New rider added: {recruited}",
            f"Assigned rider: #{rider.rider_id} at ({rider.x}, {rider.y}), "
            f"speed {rider.speed} units/tick",
            f"Estimated delivery time: {eta} tick(s), distance "
            f"{order.distance} units",
            "Route map (rider -> restaurant -> customer):",
            DisplayManager.render_map(route=route, riders=[rider]),
        ]
        return "\n".join(lines)

    def cmd_status(self, args):
        """Show system funds, riders and consistency checks."""
        riders = globalvar.get_value("riders", [])
        return DisplayManager.render_status(
            SystemManager.get_funds(),
            riders,
            int(globalvar.get_value("time", 0)),
            SystemManager.check_consistency(),
        )

    def cmd_orders(self, args):
        """Show every order and its details."""
        return DisplayManager.render_orders(
            globalvar.get_value("orders", []),
            int(globalvar.get_value("time", 0)),
        )

    def cmd_riders(self, args):
        """Show every rider status-change record."""
        return DisplayManager.render_rider_log(globalvar.get_value("riders", []))

    def cmd_map(self, args):
        """Show the ASCII map with riders and active orders."""
        return DisplayManager.render_map()

    def cmd_wait(self, args):
        """Advance the simulation by extra ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise InputError("wait expects a whole number of ticks")
        if not 1 <= count <= 10000:
            raise InputError("wait count must be between 1 and 10000")
        for _ in range(count):
            SystemManager.tick()
            if not SystemManager.is_running():
                break
        return f"Advanced {count} tick(s); simulated time is now " \
               f"{globalvar.get_value('time', 0)}."

    def cmd_save(self, args):
        """Save the system state to a JSON file."""
        path = args[0] if args else "dispatch_state.json"
        try:
            SystemManager.save_state(path)
        except OSError as exc:
            return f"Could not save state to {path}: {exc}"
        return f"State saved to {path}."

    def cmd_history(self, args):
        """List previously entered commands."""
        if not self.history:
            return "History is empty."
        return "\n".join(f"{i:>4}  {cmd}" for i, cmd in enumerate(self.history, 1))

    def cmd_help(self, args):
        """Show the command reference."""
        return HELP_TEXT

    def cmd_quit(self, args):
        """Stop the simulation loop."""
        SystemManager.shutdown()
        return "Goodbye."
