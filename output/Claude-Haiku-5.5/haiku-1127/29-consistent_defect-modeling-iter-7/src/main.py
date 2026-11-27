"""Command-line entry point for the food delivery dispatch simulator."""

import logging
import sys
from typing import Callable, Dict, List

try:  # Enables arrow-key history on platforms that provide readline.
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows without pyreadline
    pass

from display import DisplayManager
from input_manager import InputError, InputManager
from system import init_system, SystemManager

HELP_TEXT = """Commands:
  start (s) [rx ry cx cy]  Place an order: restaurant x y, customer x y (0-800).
                           Prompts for the four numbers if none are given.
  status (st)              Show system funds, riders and their orders.
  orders (o)               Show details of all orders.
  riders (r)               Show the event log of every rider.
  map (m)                  Show the ASCII map with riders and active orders.
  tick (t) [n]             Advance the simulation by n ticks (default 1).
  history (hist)           Show previously entered commands.
  save [file]              Save state to a JSON file (default dispatch_state.json).
  help (?, h)              Show this help.
  quit (q, x, exit)        Exit the program.
Shortcuts: !! repeats the last command, !n repeats history entry n."""


class Application:
    """Runs the interactive command loop.

    Attributes:
        system: The SystemManager holding simulation state.
        inputs: Parser and validator for user input.
        display: Renderer for status text and maps.
    """

    def __init__(self) -> None:
        """Initialize the system, input parser and display."""
        self.system: SystemManager = init_system()
        self.inputs = InputManager(
            min_coordinate=self.system.config["min_coordinate"],
            max_coordinate=self.system.config["max_coordinate"],
        )
        self.display = DisplayManager(
            map_size=self.system.config["grid_size"] * self.system.config["cell_size"],
            cell_size=self.system.config["cell_size"],
        )
        self.commands: Dict[str, Callable[[List[str]], None]] = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "history": self.cmd_history,
            "save": self.cmd_save,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
        }

    def run(self) -> None:
        """Run the main loop until the user quits or input ends."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands.")
        while self.system.running:
            try:
                line = input("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            self.execute(line)
        print("Goodbye.")

    def execute(self, line: str) -> None:
        """Parse and run a single command line, reporting errors gracefully.

        Args:
            line: Raw user input.
        """
        try:
            text = self.inputs.resolve(line)
        except InputError as exc:
            print(f"Error: {exc}")
            return
        if not text:
            return
        self.inputs.record(text)

        name, args = self.inputs.parse_command(text)
        handler = self.commands.get(name)
        if handler is None:
            print(f"Unknown command '{name}'. Type 'help' for the command list.")
            return
        try:
            handler(args)
        except InputError as exc:
            print(f"Input error: {exc}")
        except Exception:  # Recovery: keep the simulation alive.
            logging.getLogger(__name__).exception("Command '%s' failed", name)
            print("An internal error occurred; the system state was preserved.")

    def cmd_start(self, args: List[str]) -> None:
        """Place an order and show assignment details and the route map."""
        if args:
            coords = self.inputs.parse_coordinates(args)
        else:
            answer = input("Enter restaurant x y and customer x y: ")
            coords = self.inputs.parse_coordinates([answer])

        result = self.system.place_order(*coords)
        order = result["order"]
        rx, ry = result["restaurant"]
        cx, cy = result["customer"]
        print(f"Order #{order.id} created at tick {order.start_time}.")
        print(f"  Restaurant grid point: ({rx}, {ry})")
        print(f"  Customer grid point:   ({cx}, {cy})")

        recruited = result["recruited_rider"]
        if recruited is not None:
            print(f"  New rider added: yes (Rider #{recruited.rider_id}, "
                  f"cost {self.system.config['recruit_cost']})")
        else:
            print("  New rider added: no")

        rider = result["rider"]
        if rider is None:
            print("  No rider available; the order is queued for dispatch.")
            return
        print(f"  Assigned to Rider #{rider.rider_id} "
              f"(speed {rider.speed} units/tick)")
        print(f"  Route length: {result['route_length']} units | "
              f"estimated time: {result['eta_ticks']} ticks")
        print(self.display.render_map([rider], [order], route=result["route"]))

    def cmd_status(self, args: List[str]) -> None:
        """Show funds, riders and a consistency report."""
        print(self.display.render_status(self.system.funds, self.system.riders))
        issues = self.system.check_consistency()
        if issues:
            print("Consistency warnings:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("System state is consistent.")

    def cmd_orders(self, args: List[str]) -> None:
        """Show the order table."""
        print(self.display.render_orders(self.system.order_manager.orders))

    def cmd_riders(self, args: List[str]) -> None:
        """Show every rider's status-change log."""
        print(self.display.render_rider_log(self.system.riders))

    def cmd_map(self, args: List[str]) -> None:
        """Show the ASCII map with riders and active orders."""
        active = self.system.order_manager.active_orders()
        print(self.display.render_map(self.system.riders, active))

    def cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation clock."""
        count = self.inputs.parse_positive_int(args, default=1, maximum=1000)
        self.system.run_ticks(count)
        riders = self.system.riders
        busy = sum(1 for r in riders if r.state != 0)
        print(f"Advanced {count} tick(s). Current tick: {self.system.current_tick}. "
              f"Busy riders: {busy}/{len(riders)}.")

    def cmd_history(self, args: List[str]) -> None:
        """List previously entered commands."""
        if not self.inputs.command_history:
            print("No command history.")
            return
        for index, entry in enumerate(self.inputs.command_history, start=1):
            print(f"  {index:>3}  {entry}")

    def cmd_save(self, args: List[str]) -> None:
        """Save the current state to a JSON file."""
        path = args[0] if args else "dispatch_state.json"
        try:
            self.system.save_state(path)
        except OSError as exc:
            print(f"Could not save state: {exc}")
            return
        print(f"State saved to {path}.")

    def cmd_help(self, args: List[str]) -> None:
        """Print the command reference."""
        print(HELP_TEXT)

    def cmd_quit(self, args: List[str]) -> None:
        """Stop the main loop."""
        self.system.stop()


def main() -> None:
    """Configure logging and start the interactive application."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    Application().run()


if __name__ == "__main__":
    main()
