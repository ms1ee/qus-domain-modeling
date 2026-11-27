"""Command-line entry point for the food delivery dispatch simulator.

Run with: ``python src/main.py``
"""

import logging
import sys
from typing import Dict, List, Optional

from config import Configuration
from display import DisplayManager
from input_manager import HELP_TEXT, InputError, InputManager
from system import DispatchError, SystemManager, init_system

logger = logging.getLogger("dispatch")


class DispatchApp:
    """Interactive application wiring the system, display and input layers."""

    def __init__(self, config: Configuration,
                 input_manager: Optional[InputManager] = None) -> None:
        """Initialise the system and the user interface.

        Args:
            config: Loaded configuration.
            input_manager: Optional input manager (created if None).
        """
        self.config = config
        self.system: SystemManager = init_system(config)
        self.display = DisplayManager(self.system.grid)
        self.inputs = input_manager or InputManager()
        self._handlers = {
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

    def run(self) -> int:
        """Run the command loop until the user quits.

        Returns:
            Process exit code (0 on normal exit).
        """
        print("Food Delivery Order Dispatch Simulator (8x8 grid, 800x800 units)")
        print("Type 'help' for commands.")
        while self.system.is_running:
            try:
                line = self.inputs.read_command()
                if not line:
                    continue
                name, args = self.inputs.parse(line)
                self._handlers[name](args)
            except (EOFError, KeyboardInterrupt):
                print()
                self._cmd_quit([])
                break
            except InputError as exc:
                print(f"[input error] {exc}")
            except DispatchError as exc:
                print(f"[dispatch error] {exc}")
            except Exception:  # noqa: BLE001 - keep the program alive
                logger.exception("Unexpected failure while handling a command")
                print("[error] unexpected failure; system state was preserved.")
        return 0

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _cmd_start(self, args: List[str]) -> None:
        """Create an order from restaurant and customer coordinates.

        Args:
            args: Optional four coordinate tokens.
        """
        if args:
            coords = self.inputs.parse_coordinates(args)
        else:
            print("Enter restaurant and customer positions (integers 0-800):")
            coords = self.inputs.prompt_coordinates()
        restaurant = (coords[0], coords[1])
        customer = (coords[2], coords[3])
        result = self.system.submit_order(restaurant, customer)
        order = result["order"]
        rider = result["rider"]
        print(f"Order #{order.id} accepted at tick {order.start_time}.")
        print(f"  Restaurant input {restaurant} -> grid point {result['restaurant']}")
        print(f"  Customer input   {customer} -> grid point {result['customer']}")
        print(f"  New rider recruited: {'yes' if result['new_rider'] else 'no'}")
        print(f"  Assigned rider: #{rider.rider_id} (speed {result['speed']} units/tick)")
        print(f"  Planned distance: {result['distance']:.0f} units, "
              f"estimated time: {result['estimated_ticks']} ticks")
        print("  Route map (advance time with 'tick'):")
        print(self.display.render_map(
            routes=[result["route"]], riders=[rider], orders=[order]
        ))

    def _cmd_status(self, args: List[str]) -> None:
        """Print the system status snapshot.

        Args:
            args: Unused.
        """
        print(self.display.render_status(
            self.system.funds, self.system.riders, self.system.current_tick
        ))

    def _cmd_orders(self, args: List[str]) -> None:
        """Print the order table.

        Args:
            args: Unused.
        """
        print(self.display.render_orders(self.system.order_manager.orders))

    def _cmd_riders(self, args: List[str]) -> None:
        """Print every rider's status-change log.

        Args:
            args: Unused.
        """
        print(self.display.render_rider_logs(self.system.riders))

    def _cmd_map(self, args: List[str]) -> None:
        """Print the ASCII map with riders, orders and active routes.

        Args:
            args: Unused.
        """
        routes = [[(r.x, r.y)] + list(r.route) for r in self.system.riders if r.route]
        print(self.display.render_map(
            routes=routes,
            riders=self.system.riders,
            orders=self.system.order_manager.active_orders(),
        ))

    def _cmd_tick(self, args: List[str]) -> None:
        """Advance the simulation by one or more ticks.

        Args:
            args: Optional tick count.
        """
        count = self.inputs.parse_tick_count(args)
        for _ in range(count):
            self.system.tick()
        print(f"Advanced {count} tick(s); current tick {self.system.current_tick}. "
              f"Funds: {self.system.funds}. Active orders: "
              f"{len(self.system.order_manager.active_orders())}.")

    def _cmd_history(self, args: List[str]) -> None:
        """Print the command history.

        Args:
            args: Unused.
        """
        if not self.inputs.command_history:
            print("History is empty.")
            return
        for index, entry in enumerate(self.inputs.command_history, start=1):
            print(f"  {index:>3}  {entry}")

    def _cmd_help(self, args: List[str]) -> None:
        """Print the help text.

        Args:
            args: Unused.
        """
        print(HELP_TEXT)

    def _cmd_quit(self, args: List[str]) -> None:
        """Save state if enabled and stop the main loop.

        Args:
            args: Unused.
        """
        if self.config.save_on_exit:
            try:
                path = self.system.save_state()
                print(f"State saved to {path}.")
            except OSError as exc:
                print(f"[warning] could not save state: {exc}")
        self.system.is_running = False
        print("Goodbye.")


def main() -> int:
    """Program entry point.

    Returns:
        Process exit code.
    """
    config = Configuration.load()
    level = getattr(logging, str(config.log_level).upper(), logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = DispatchApp(config)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
