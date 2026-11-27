"""Command parsing, input validation and command dispatch."""

import logging

from display import DisplayManager
from path_planner import MAP_SIZE, cell_index_of
from order_model import Order

logger = logging.getLogger(__name__)

WELCOME = (
    "Food Delivery Dispatch Simulator. Type 'help' for commands. "
    "Each prompt advances the simulation by one tick."
)

HELP_TEXT = """Commands:
  start [rx ry cx cy]  place an order (restaurant then customer, 0-800);
                       prompts for missing coordinates
  status               show funds, riders and their states
  orders               show all orders with timing and distance
  riders               show every rider status change
  map                  show the ASCII map
  wait [n]             advance n ticks (default 1, max 1000)
  save [file]          save state as JSON (default simulation_state.json)
  history              list previous commands
  !! / !n              repeat the last command / the n-th command
  help                 show this help
  quit / exit          leave the simulator
Shortcuts: s=start st=status o=orders r=riders m=map w=wait sv=save
           h or ?=help q or e=quit"""

ALIASES = {
    "s": "start",
    "st": "status",
    "o": "orders",
    "r": "riders",
    "m": "map",
    "w": "wait",
    "sv": "save",
    "h": "help",
    "?": "help",
    "hist": "history",
    "q": "quit",
    "e": "exit",
}


class InputManager:
    """Parses user commands and renders responses.

    Attributes:
        system: The :class:`SystemManager` being controlled.
        display: The :class:`DisplayManager` used for output.
        command_history: Executed command lines in order.
    """

    def __init__(self, system, display=None):
        """Create the input manager.

        Args:
            system: The :class:`SystemManager` to control.
            display: Optional DisplayManager. Created when omitted.
        """
        self.system = system
        self.display = display or DisplayManager(system)
        self.command_history = []

    def parse_coordinates(self, tokens):
        """Validate four coordinate tokens.

        Args:
            tokens: Sequence of four strings.

        Returns:
            List of four ints.

        Raises:
            ValueError: If the count, type or range is invalid.
        """
        if len(tokens) != 4:
            raise ValueError("expected 4 coordinates: restaurant_x "
                             "restaurant_y customer_x customer_y")
        values = []
        for token in tokens:
            try:
                value = int(token)
            except (TypeError, ValueError):
                raise ValueError(f"'{token}' is not an integer") from None
            if not 0 <= value <= MAP_SIZE:
                raise ValueError(f"{value} is out of range 0-{MAP_SIZE}")
            values.append(value)
        return values

    def run(self, input_func=input, output_func=print):
        """Run the interactive main loop.

        Each iteration advances the simulation by one tick, then reads and
        executes one command.

        Args:
            input_func: Function used to read a line (default ``input``).
            output_func: Function used to print output (default ``print``).
        """
        output_func(WELCOME)
        while self.system.is_running:
            self.system.tick()
            try:
                line = input_func("dispatch> ")
            except EOFError:
                output_func("\nInput closed, exiting.")
                break
            except KeyboardInterrupt:
                output_func("\nInterrupted, exiting.")
                break
            text = self.handle(line, input_func)
            if text:
                output_func(text)
        self.system.is_running = False

    def handle(self, line, input_func=input):
        """Execute one command line and return the textual response.

        Args:
            line: Raw command text.
            input_func: Function used for follow-up prompts.

        Returns:
            Response text (may be empty).
        """
        text = (line or "").strip()
        if not text:
            return ""
        if text.startswith("!"):
            text = self._resolve_history(text)
            if text is None:
                return "Error: no matching command in history."
        self.command_history.append(text)
        try:
            return self._dispatch(text, input_func)
        except ValueError as exc:
            return f"Error: {exc}"
        except Exception as exc:  # recovery: keep the simulation running
            logger.exception("Command '%s' failed", text)
            return f"Unexpected error: {exc}. The simulation state was kept."

    def _resolve_history(self, text):
        """Resolve ``!!`` or ``!n`` shortcuts to a previous command line.

        Args:
            text: The shortcut text beginning with ``!``.

        Returns:
            The referenced command line, or None if it cannot be resolved.
        """
        if not self.command_history:
            return None
        ref = text[1:].strip()
        if ref in ("", "!"):
            return self.command_history[-1]
        if ref.isdigit():
            index = int(ref) - 1
            if 0 <= index < len(self.command_history):
                return self.command_history[index]
        return None

    def _dispatch(self, text, input_func):
        """Route a command to its handler.

        Args:
            text: Command line.
            input_func: Function used for follow-up prompts.

        Returns:
            Response text.
        """
        parts = text.split()
        command = ALIASES.get(parts[0].lower(), parts[0].lower())
        args = parts[1:]
        if command == "start":
            return self._cmd_start(args, input_func)
        if command == "status":
            return self.display.render_status()
        if command == "orders":
            return self.display.render_orders()
        if command == "riders":
            return self.display.render_rider_log()
        if command == "map":
            return self.display.render_map()
        if command == "wait":
            return self._cmd_wait(args)
        if command == "save":
            return self._cmd_save(args)
        if command == "history":
            return self._cmd_history()
        if command == "help":
            return HELP_TEXT
        if command in ("quit", "exit"):
            self.system.is_running = False
            return "Goodbye."
        return f"Unknown command '{parts[0]}'. Type 'help' for a list."

    def _cmd_start(self, args, input_func):
        """Place an order and show the assignment and route map.

        Args:
            args: Coordinate tokens supplied on the command line.
            input_func: Function used to prompt for missing coordinates.

        Returns:
            Response text.
        """
        tokens = list(args)
        labels = ("restaurant x", "restaurant y", "customer x", "customer y")
        while len(tokens) < 4:
            raw = input_func(f"  {labels[len(tokens)]} (0-{MAP_SIZE}): ")
            tokens.extend((raw or "").split())
        rx, ry, cx, cy = self.parse_coordinates(tokens)

        order, rider, new_rider = self.system.submit_order((rx, ry), (cx, cy))
        res_cell = cell_index_of(rx, ry)
        cus_cell = cell_index_of(cx, cy)
        lines = [
            f"Order #{order.id} created at tick {order.start_time}",
            f"Restaurant: cell {res_cell} centre {order.restaurant_pos}",
            f"Customer: cell {cus_cell} centre {order.customer_pos}",
            f"New rider added: {'yes' if new_rider else 'no'}",
        ]
        if rider is None:
            lines.append("No rider available; the order is pending until "
                         "funds allow recruitment.")
            return "\n".join(lines)

        segments, total, estimated = self.system.preview_route(
            rider.position, order.restaurant_pos, order.customer_pos,
            rider.speed)
        lines.extend([
            f"Assigned rider: {rider.rider_id} "
            f"(status {rider.state_name}, speed {rider.speed} units/tick)",
            f"Route distance: {total:.1f} units, estimated time: "
            f"{estimated} ticks",
            "Route map (from rider's current position):",
            self.display.render_map(segments),
        ])
        return "\n".join(lines)

    def _cmd_wait(self, args):
        """Advance the simulation by one or more ticks.

        Args:
            args: Optional tick count.

        Returns:
            Response text.

        Raises:
            ValueError: If the count is invalid.
        """
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                raise ValueError(f"'{args[0]}' is not an integer") from None
        if not 1 <= count <= 1000:
            raise ValueError("wait count must be between 1 and 1000")
        for _ in range(count):
            self.system.tick()
        return f"Advanced {count} tick(s); now at tick {self.system.current_time}."

    def _cmd_save(self, args):
        """Save the system state to a JSON file.

        Args:
            args: Optional file path.

        Returns:
            Response text.
        """
        path = args[0] if args else "simulation_state.json"
        self.system.save_state(path)
        return f"State saved to {path}."

    def _cmd_history(self):
        """List previously executed commands.

        Returns:
            Response text.
        """
        if not self.command_history:
            return "No commands yet."
        return "\n".join(f"{i:>3}  {cmd}"
                         for i, cmd in enumerate(self.command_history, 1))
