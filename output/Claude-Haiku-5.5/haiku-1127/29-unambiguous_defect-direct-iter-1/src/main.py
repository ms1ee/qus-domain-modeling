"""Command-line entry point for the food delivery dispatch simulator.

Run with:  python src/main.py [--config path/to/config.json] [--debug]
"""

import argparse
import logging
import sys

import config
import order as order_service
import system
from display import DisplayManager
from input_manager import InputManager

logger = logging.getLogger("dispatch")

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] [n]  Create an order; restaurant then customer (0-800).
                           Prompts for coordinates when none are given.
  status              [s]  Show funds, tick, and every rider's state and orders.
  orders              [o]  Show all orders with timing and assignment data.
  riders              [r]  Show every rider's status-change log.
  tick [N]            [t]  Advance simulated time by N ticks (default 1).
  map                 [m]  Show the ASCII map with riders and active orders.
  save [file]         [v]  Save funds, riders and orders as JSON.
  help                [h]  Show this help.
  quit | exit         [q/x] Leave the program.
Up/down arrow keys recall history when readline is available."""


class DispatchApp:
    """Interactive command loop tying together input, services and display."""

    MAX_TICKS_PER_COMMAND = 1000

    def __init__(self, input_manager=None, display=None):
        """Create the application.

        Args:
            input_manager: Optional InputManager; a default one is created
                when omitted.
            display: Optional DisplayManager; a default one is created when
                omitted.
        """
        self.input = input_manager or InputManager()
        self.display = display or DisplayManager()
        self.commands = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "tick": self.cmd_tick,
            "map": self.cmd_map,
            "save": self.cmd_save,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    def run(self):
        """Run the command loop until the user quits.

        Returns:
            int: Process exit code (0 on normal exit).
        """
        self.input.enable_history()
        print("Food delivery dispatch simulator. Type 'help' for commands.")
        while system.is_running():
            try:
                line = self.input.read_command("dispatch> ")
            except (EOFError, KeyboardInterrupt):
                print()
                system.stop_system()
                break
            if not line:
                continue
            command, args = self.input.parse_command(line)
            handler = self.commands.get(command)
            if handler is None:
                print(f"Unknown command '{command}'. Type 'help' for the list.")
                continue
            try:
                handler(args)
            except Exception as exc:  # noqa: BLE001 - recover and continue
                logger.exception("Command '%s' failed", command)
                print(f"Error: {exc}. The system state has been preserved.")
        print("Goodbye.")
        return 0

    def cmd_start(self, args):
        """Create an order, assign a rider and show the planned route.

        Args:
            args: Optional four coordinate tokens.
        """
        if args:
            try:
                coords = self.input.parse_coordinates(" ".join(args))
            except ValueError as exc:
                print(f"Invalid input: {exc}.")
                return
        else:
            coords = self.input.prompt_coordinates()
            if coords is None:
                print("Order cancelled.")
                return

        try:
            order = order_service.create_order(coords)
        except ValueError as exc:
            print(f"Invalid order: {exc}.")
            return

        riders_before = len(system.get_riders())
        try:
            rider = order_service.dispatch_order(order)
        except Exception as exc:  # noqa: BLE001 - roll back the order
            order_service.cancel_order(order)
            logger.exception("Dispatch failed for order %s", order.id)
            print(f"Could not dispatch order: {exc}.")
            return

        print(f"Order #{order.id} accepted at tick {order.created_tick}.")
        print(f"  Restaurant grid position: {order.res_pos}")
        print(f"  Customer grid position:   {order.cus_pos}")
        if len(system.get_riders()) > riders_before:
            print(f"  New rider recruited: #{rider.rider_id} "
                  f"(cost {config.CONFIG['recruit_cost']}).")
        print(f"  Assigned to rider #{rider.rider_id} at {rider.position}, "
              f"state {rider.state_name}, speed {rider.speed}.")
        print(self.display.render_route(rider, order))

    def cmd_status(self, args):
        """Print the system status snapshot."""
        print(self.display.render_status(
            system.get_funds(), system.get_tick(), system.get_riders()))

    def cmd_orders(self, args):
        """Print the table of all orders."""
        print(self.display.render_orders(order_service.get_all_orders()))

    def cmd_riders(self, args):
        """Print the status-change history of all riders."""
        print(self.display.render_rider_logs(system.get_riders()))

    def cmd_tick(self, args):
        """Advance simulated time.

        Args:
            args: Optional number of ticks.
        """
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                print("Tick count must be an integer.")
                return
            if not 1 <= count <= self.MAX_TICKS_PER_COMMAND:
                print(f"Tick count must be between 1 and "
                      f"{self.MAX_TICKS_PER_COMMAND}.")
                return
        for _ in range(count):
            system.advance_tick()
        print(f"Advanced {count} tick(s). Current tick: {system.get_tick()}.")

    def cmd_map(self, args):
        """Print the ASCII map with riders and active orders."""
        active = [o for o in order_service.get_all_orders() if not o.is_completed()]
        print(self.display.render_map(system.get_riders(), active))

    def cmd_save(self, args):
        """Save the simulation state as JSON.

        Args:
            args: Optional destination path.
        """
        path = args[0] if args else "dispatch_state.json"
        try:
            system.save_snapshot(path)
        except OSError as exc:
            print(f"Could not save state: {exc}.")
            return
        print(f"State saved to {path}.")

    def cmd_help(self, args):
        """Print the command reference."""
        print(HELP_TEXT)

    def cmd_quit(self, args):
        """Stop the main loop."""
        system.stop_system()


def main(argv=None):
    """Parse arguments, initialise the system and run the command loop.

    Args:
        argv: Optional list of command-line arguments.

    Returns:
        int: Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None,
                        help="path to a JSON configuration file")
    parser.add_argument("--debug", action="store_true",
                        help="enable debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.config:
        config.load_config(args.config)
    system.init_system()
    return DispatchApp().run()


if __name__ == "__main__":
    sys.exit(main())
