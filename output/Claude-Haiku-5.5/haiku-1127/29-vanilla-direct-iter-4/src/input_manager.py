"""Command-line interface: command parsing, input validation and dispatch."""

import logging
import math
import os

import globalvar
from display import DisplayManager
from order_model import validate_order_coordinates

try:  # Enables arrow-key editing and in-session command history where available.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform dependent
    readline = None

logger = logging.getLogger(__name__)

ALIASES = {
    "a": "start",
    "s": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "t": "tick",
    "w": "save",
    "h": "help",
    "?": "help",
    "q": "quit",
    "x": "exit",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  Create an order (restaurant then customer, 0-800). Prompts if omitted.
  status               System funds, riders and their status/orders.
  orders               All orders with timing, distance and rider.
  riders               Status-change log of every rider.
  map                  ASCII map with riders and active orders.
  tick [n]             Advance the simulation by n ticks (default 1).
  run                  Advance until all orders are delivered (or a limit is reached).
  save [path]          Save system state to a JSON file.
  history              Show commands entered in this session.
  help                 Show this help.
  quit / exit          Leave the program.
Shortcuts: a=start s=status o=orders r=riders m=map t=tick w=save h=help q=quit x=exit
"""


class InputManager:
    """Parses user commands, validates input and prints results."""

    def __init__(self, system, input_func=None, output_func=None):
        """Create the command interface.

        Args:
            system: SystemManager instance.
            input_func: Callable used to read a line (defaults to ``input``).
            output_func: Callable used to print text (defaults to ``print``).
        """
        self.system = system
        self.display = DisplayManager()
        self.history = []
        self._input = input_func or input
        self._print = output_func or print
        self._handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "run": self.cmd_run,
            "save": self.cmd_save,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    def run(self):
        """Run the interactive main loop until quit or end of input."""
        self._print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while globalvar.get_value("running", False):
            try:
                line = self._input("dispatch> ")
            except EOFError:
                self._print("")
                break
            except KeyboardInterrupt:
                self._print("\nInterrupted. Exiting.")
                break
            self.handle_line(line)
        globalvar.set_value("running", False)

    def handle_line(self, line):
        """Execute one command line with error handling and recovery.

        Args:
            line: Raw text entered by the user.
        """
        text = (line or "").strip()
        if not text:
            return
        self.history.append(text)
        parts = text.split()
        name = ALIASES.get(parts[0].lower(), parts[0].lower())
        handler = self._handlers.get(name)
        if handler is None:
            self._print(f"Unknown command '{parts[0]}'. Type 'help' for the command list.")
            return
        try:
            handler(parts[1:])
        except (ValueError, TypeError) as exc:
            self._print(f"Input error: {exc}")
        except OSError as exc:
            self._print(f"I/O error: {exc}")
        except Exception as exc:  # recover and keep the simulator running
            logger.exception("Unexpected error while running '%s'", text)
            repaired = self.system.repair()
            self._print(f"Internal error: {exc}. State repaired ({repaired} fix(es)).")

    def _parse_coordinates(self, tokens):
        """Parse four integer coordinates from tokens (commas allowed).

        Raises:
            ValueError: If the count or type of values is wrong or out of range.
        """
        parts = " ".join(tokens).replace(",", " ").split()
        if len(parts) != 4:
            raise ValueError("expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y")
        try:
            values = [int(part) for part in parts]
        except ValueError:
            raise ValueError("coordinates must be integers")
        return validate_order_coordinates(values)

    def _prompt_coordinates(self):
        """Prompt repeatedly until valid coordinates or cancellation."""
        self._print("Enter restaurant x, y and customer x, y (0-800), "
                    "e.g. 150 250 350 450. Empty line cancels.")
        while True:
            text = self._input("start> ").strip()
            if not text:
                self._print("Cancelled.")
                return None
            try:
                return self._parse_coordinates(text.split())
            except (ValueError, TypeError) as exc:
                self._print(f"Invalid input: {exc}. Try again.")

    def _find_rider(self, rider_id):
        """Return the rider with the given id, or None."""
        for rider in globalvar.get_value("riders") or []:
            if rider.rider_id == rider_id:
                return rider
        return None

    def cmd_start(self, args):
        """Create an order, dispatch it and show the planned route."""
        coords = self._parse_coordinates(args) if args else self._prompt_coordinates()
        if coords is None:
            return
        order = self.system.order_manager.create_order(coords)
        recruited, assigned = self.system.dispatch()
        funds = self.system.funds
        rx, ry, cx, cy = coords

        self._print(f"Order #{order.id} created at tick {order.start_time}:")
        self._print(f"  Restaurant: input ({rx}, {ry}) -> grid cell "
                    f"({rx // 100}, {ry // 100}), centre {order.res_pos}")
        self._print(f"  Customer:   input ({cx}, {cy}) -> grid cell "
                    f"({cx // 100}, {cy // 100}), centre {order.cus_pos}")
        if recruited:
            ids = ", ".join(f"#{r.rider_id}" for r in recruited)
            self._print(f"  New rider added: yes ({ids}); funds now {funds}")
        else:
            self._print(f"  New rider added: no; funds {funds}")

        rider = self._find_rider(order.rider_id)
        if rider is None:
            self._print(f"  No rider available. Order #{order.id} stays pending.")
            return

        distance = math.hypot(rider.x - order.res_pos[0], rider.y - order.res_pos[1])
        self._print(f"  Assigned to rider #{rider.rider_id} "
                    f"(distance to restaurant {distance:.1f} units)")
        earlier = len([1 for o, _ in assigned if o is not order])
        if earlier:
            self._print(f"  Also assigned {earlier} earlier pending order(s).")

        points, total = self.system.order_manager.estimate_route(rider, order)
        speed = rider.speed if rider.speed > 0 else 1
        ticks = math.ceil(total / speed)
        self._print(f"  Route: {total} units, speed {rider.speed} units/tick, "
                    f"estimated time {ticks} ticks")
        if len(rider.orders) > 1:
            self._print("  Note: the rider has queued orders; the route above "
                        "starts from its current position.")
        self._print(self.display.render_map(route=points, origin=rider.position))

    def cmd_status(self, args):
        """Show funds, rider states and consistency checks."""
        active = sum(1 for o in globalvar.get_value("orders") if o.status != "completed")
        self._print(self.display.format_status(
            self.system.funds, self.system.riders, active))
        problems = self.system.check_consistency()
        if problems:
            self._print("Consistency warnings:")
            for problem in problems:
                self._print(f"  - {problem}")
        else:
            self._print("State consistency: OK")

    def cmd_orders(self, args):
        """Show all orders."""
        self._print(self.display.format_orders(globalvar.get_value("orders")))

    def cmd_riders(self, args):
        """Show every rider's recorded status changes."""
        self._print(self.display.format_rider_logs(globalvar.get_value("riders")))

    def cmd_map(self, args):
        """Show the ASCII map."""
        self._print(self.display.render_map())

    def cmd_tick(self, args):
        """Advance the simulation by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError("tick count must be an integer")
        if not 1 <= count <= 1000:
            raise ValueError("tick count must be between 1 and 1000")
        for _ in range(count):
            self._report_tick(self.system.tick())
        self._print(f"Current tick: {self.system.tick_count}")

    def _report_tick(self, report):
        """Print the notable events of one tick."""
        events = []
        if report["recruited"]:
            events.append("recruited " + ", ".join(f"#{r}" for r in report["recruited"]))
        for order_id, rider_id in report["assigned"]:
            events.append(f"order #{order_id} -> rider #{rider_id}")
        for order_id in report["completed"]:
            events.append(f"order #{order_id} delivered")
        if events:
            self._print(f"tick {report['tick']}: " + "; ".join(events))

    def cmd_run(self, args):
        """Advance the simulation until all orders are delivered or a limit hits."""
        limit = self.system_limit()
        ticks = 0
        while self.system.has_active_orders() and ticks < limit:
            self._report_tick(self.system.tick())
            ticks += 1
        if self.system.has_active_orders():
            self._print(f"Stopped after {ticks} ticks with unfinished orders "
                        "(insufficient funds or limit reached).")
        else:
            self._print(f"All orders delivered by tick {self.system.tick_count}.")

    def system_limit(self):
        """Maximum number of ticks the run command may advance."""
        return int(self.system.params.get("max_run_ticks", 10000))

    def cmd_save(self, args):
        """Save the system state to a JSON file."""
        path = args[0] if args else os.path.join(os.getcwd(), "dispatch_state.json")
        self.system.save_state(path)
        self._print(f"State saved to {path}")

    def cmd_history(self, args):
        """List commands entered in this session."""
        if not self.history:
            self._print("No commands yet.")
            return
        for index, entry in enumerate(self.history, start=1):
            self._print(f"  {index:>3}  {entry}")

    def cmd_help(self, args):
        """Show the command reference."""
        self._print(HELP_TEXT)

    def cmd_quit(self, args):
        """Exit the program."""
        globalvar.set_value("running", False)
        self._print("Goodbye.")
