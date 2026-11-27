"""SystemManager: ties together all modules and runs the main loop."""

import json
import logging

import globalvar
import system
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from path_planner import GridMap, PathPlanner

logger = logging.getLogger(__name__)


class SystemManager:
    """Core class managing funds, riders, orders and the main loop."""

    def __init__(self, config=None, save_on_exit=True):
        system.init_system(config)
        cfg = globalvar.get_value("config")
        self.grid = GridMap(cfg["map_size"], cfg["cell_size"])
        self.planner = PathPlanner(self.grid)
        self.order_manager = OrderManager(self.planner)
        self.display = DisplayManager(self.grid)
        self.input_manager = InputManager(max_coord=self.grid.map_size)
        self.state_file = cfg.get("state_file", "dispatch_state.json")
        self.save_on_exit = save_on_exit

    # ------------------------------------------------------------ properties
    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        return globalvar.get_value("riders") or []

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0)

    @property
    def recruitment_cost(self):
        return globalvar.get_value("recruitment_cost", 0)

    # ------------------------------------------------------------ simulation
    def tick(self, n=1):
        """Advance the simulation ``n`` ticks."""
        for _ in range(n):
            system.advance_tick()
            system.check_consistency()
        return self.current_tick

    # -------------------------------------------------------------- commands
    def handle_command(self, line):
        """Execute one command line and return its output text."""
        try:
            cmd, args = self.input_manager.parse_command(line)
        except ValueError as exc:
            return "Error: %s" % exc
        if not cmd:
            return ""
        handler = getattr(self, "cmd_" + cmd, None)
        if handler is None:
            return "Unknown command '%s'. Type 'help' for commands." % cmd
        try:
            return handler(args)
        except ValueError as exc:
            return "Error: %s" % exc
        except Exception as exc:  # graceful recovery
            logger.exception("Command %s failed", cmd)
            system.check_consistency()
            return "Internal error (%s); system state recovered." % exc

    def cmd_start(self, args):
        if not args.strip():
            try:
                args = self.input_manager.read_line(
                    "Enter restaurant_x restaurant_y customer_x customer_y "
                    "(0-%d): " % self.grid.map_size)
            except (EOFError, KeyboardInterrupt):
                return "Order input cancelled."
        coords = self.input_manager.parse_coordinates(args)
        result = self.order_manager.submit(coords)
        return self.display.format_start_result(result, self.funds)

    def cmd_status(self, args):
        return self.display.format_status(self.funds, self.current_tick,
                                          self.riders,
                                          self.order_manager.orders)

    def cmd_orders(self, args):
        text = self.display.format_orders(self.order_manager.orders)
        stats = self.order_manager.statistics()
        return text + "\nTotal %d, completed %d, active %d, avg time %s" % (
            stats["total"], stats["completed"], stats["active"],
            stats["average_time"] if stats["average_time"] is not None else "-")

    def cmd_riders(self, args):
        return self.display.format_rider_logs(self.riders)

    def cmd_map(self, args):
        return self.display.render_map(self.riders,
                                       self.order_manager.active_orders())

    def cmd_step(self, args):
        n = self.input_manager.parse_step_count(args)
        # The main loop advances one more tick after the command.
        if n > 1:
            self.tick(n - 1)
        return "Advancing %d tick(s)." % n

    def cmd_history(self, args):
        return self.input_manager.history_text()

    def cmd_help(self, args):
        return self.display.help_text()

    def cmd_save(self, args):
        path = args.strip() or self.state_file
        self.save_state(path)
        return "State saved to %s" % path

    def cmd_quit(self, args):
        globalvar.set_value("running", False)
        return "Goodbye."

    # ----------------------------------------------------------- persistence
    def to_dict(self):
        """JSON-serialisable snapshot of the whole system."""
        return {
            "config": globalvar.get_value("config"),
            "funds": self.funds,
            "tick": self.current_tick,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.orders],
        }

    def save_state(self, path=None):
        """Write the system snapshot as JSON."""
        path = path or self.state_file
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    # ------------------------------------------------------------- main loop
    def run(self):
        """Interactive main loop; each iteration is one simulated tick."""
        print("Food Delivery Order Dispatch System")
        print("Funds: %d. Type 'help' for commands." % self.funds)
        while self.running:
            try:
                line = self.input_manager.read_line(
                    "[t=%d] > " % self.current_tick)
            except (EOFError, KeyboardInterrupt):
                print()
                globalvar.set_value("running", False)
                break
            output = self.handle_command(line)
            if output:
                print(output)
            if self.running:
                self.tick()
        if self.save_on_exit:
            try:
                self.save_state()
            except OSError as exc:
                logger.warning("Could not save state: %s", exc)
