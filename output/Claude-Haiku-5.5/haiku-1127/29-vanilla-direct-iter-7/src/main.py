"""Command-line entry point for the food delivery dispatch simulator.

Run from the project root with:
    python src/main.py [--config PATH] [--save PATH] [--debug]
"""

import argparse
import logging
import sys

import globalvar
from constants import MAX_SIM_TICKS
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from path_planner import PathPlanner
from system import SystemManager, apply_config, init_system, load_config

logger = logging.getLogger("dispatch")

BANNER = (
    "=== Food Delivery Order Dispatch System ===\n"
    "Grid: 8x8 cells of 100 units (0-800). Type 'help' for commands."
)


class DispatchApp:
    """Interactive application that wires the modules together.

    Args:
        input_manager: InputManager used to read commands (optional).
        config_path: Optional JSON configuration file to load at startup.
        save_path: Optional JSON file to write system state to on exit.
        output: Callable used for printing (default: print).
    """

    def __init__(self, input_manager=None, config_path=None, save_path=None,
                 output=print):
        self.out = output
        self.input = input_manager or InputManager(output=output)
        self.save_path = save_path
        self.display = DisplayManager()
        init_system()
        if config_path:
            apply_config(load_config(config_path))
        self.system = SystemManager()
        self.orders = OrderManager(self.system)
        self._handlers = {
            "start": self.cmd_start,
            "status": self.cmd_status,
            "orders": self.cmd_orders,
            "riders": self.cmd_riders,
            "map": self.cmd_map,
            "tick": self.cmd_tick,
            "run": self.cmd_run,
            "history": self.cmd_history,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }

    # Main loop --------------------------------------------------------------
    def run(self):
        """Run the interactive command loop until quit/exit or end of input."""
        self.out(BANNER)
        while globalvar.get_value("running", True):
            try:
                cmd, args = self.input.read_command()
            except (EOFError, KeyboardInterrupt):
                self.out("")
                self.cmd_quit([])
                break
            except Exception as exc:  # noqa: BLE001
                logger.exception("Input error")
                self.out(f"Error reading input: {exc}")
                continue
            if not cmd:
                continue
            self.execute(cmd, args)
        self.shutdown()

    def execute(self, cmd, args):
        """Dispatch a parsed command, guarding against unexpected errors."""
        handler = self._handlers.get(cmd)
        if handler is None:
            self.out(f"Unknown command '{cmd}'. Type 'help' for the command list.")
            return
        try:
            handler(args)
        except Exception as exc:  # noqa: BLE001 - keep the simulation alive
            logger.exception("Command %s failed", cmd)
            self.out(f"Error while running '{cmd}': {exc}. State was preserved.")

    def shutdown(self):
        """Save state when requested and report the exit."""
        if self.save_path:
            try:
                self.system.save_state(self.save_path)
                self.out(f"State saved to {self.save_path}.")
            except OSError as exc:
                self.out(f"Could not save state: {exc}")
        self.out("Goodbye.")

    # Commands ---------------------------------------------------------------
    def cmd_start(self, args):
        """Create an order, assign a rider and show the projected route."""
        if args:
            try:
                coords = self.input.parse_coordinates(args)
            except ValueError as exc:
                self.out(f"Invalid input: {exc}.")
                return
        else:
            coords = self.input.prompt_coordinates()
            if coords is None:
                return
        try:
            order = self.orders.create_order(coords)
        except ValueError as exc:
            self.out(f"Invalid order: {exc}.")
            return

        result = self.orders.dispatch(order)
        self.out(f"Order {order.id} created at tick {order.start_time}.")
        self.out(f"  Restaurant: input {order.input_res} -> grid centre {order.res_pos}")
        self.out(f"  Customer:   input {order.input_cus} -> grid centre {order.cus_pos}")
        rider = result["rider"]
        if result["recruited"] is not None:
            self.out(f"  New rider added: R{result['recruited'].rider_id} "
                     f"(recruitment cost deducted, funds now {self.system.funds}).")
        else:
            self.out("  No new rider added.")
        if rider is None:
            self.out(f"  No rider available (funds {self.system.funds}). "
                     f"Order {order.id} is pending and will be retried on each tick.")
            return
        self.out(f"  Assigned to R{rider.rider_id} "
                 f"(now at ({rider.x},{rider.y}), status: queued).")
        points, ticks = PathPlanner.project_route(
            rider.position, [order.res_pos, order.cus_pos], rider.speed)
        self.out(self.display.render_route(order, points, rider.speed, ticks))

    def cmd_status(self, args):
        """Show funds, riders and their state."""
        self.out(self.display.render_status(
            self.system.funds,
            self.system.rider_list(),
            self.system.current_tick(),
            len(self.orders.pending_list()),
        ))

    def cmd_orders(self, args):
        """Show all orders with timing and assignment details."""
        self.out(self.display.render_orders(self.orders.order_history()))

    def cmd_riders(self, args):
        """Show every recorded rider status change."""
        self.out(self.display.render_rider_logs(self.system.rider_list()))

    def cmd_map(self, args):
        """Show the ASCII map."""
        self.out(self.display.render_map(self.system.rider_list(),
                                         self.orders.order_history()))

    def _advance(self, count):
        """Advance the simulation by ``count`` ticks."""
        for _ in range(count):
            self.orders.process_pending()
            self.system.tick()

    def cmd_tick(self, args):
        """Advance the simulation by one or more ticks."""
        count = 1
        if args:
            try:
                count = int(args[0])
            except ValueError:
                self.out("Usage: tick [n] where n is a positive integer.")
                return
            if not 1 <= count <= MAX_SIM_TICKS:
                self.out(f"n must be between 1 and {MAX_SIM_TICKS}.")
                return
        self._advance(count)
        self.out(f"Advanced {count} tick(s). Current tick: {self.system.current_tick()}.")

    def cmd_run(self, args):
        """Advance until every active order has been delivered."""
        start = self.system.current_tick()
        steps = 0
        while self.orders.active_orders() and steps < MAX_SIM_TICKS:
            self._advance(1)
            steps += 1
        if self.orders.active_orders():
            self.out(f"Stopped after {steps} ticks; orders still active.")
        else:
            self.out(f"All orders delivered after {self.system.current_tick() - start} tick(s).")

    def cmd_history(self, args):
        """Show recent commands."""
        self.out(self.input.history_text())

    def cmd_help(self, args):
        """Show the command list."""
        self.out(self.input.help_text())

    def cmd_quit(self, args):
        """Stop the main loop."""
        globalvar.set_value("running", False)


def main(argv=None):
    """Parse command-line arguments and run the application.

    Args:
        argv: Optional list of arguments (default: sys.argv[1:]).

    Returns:
        int: Process exit code.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="JSON file with system parameters")
    parser.add_argument("--save", help="JSON file to write system state to on exit")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    options = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if options.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        app = DispatchApp(config_path=options.config, save_path=options.save)
        app.run()
    except KeyboardInterrupt:
        print()
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
