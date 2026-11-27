"""System initialisation and the SystemManager core class."""

import json
import logging

import globalvar
from config import Configuration
from display import DisplayManager
from grid_map import GridMap
from input_manager import InputError, InputManager
from order import InvalidOrderError, OrderManager
from order_model import Order
from path_planner import PathPlanner
from rider import Rider, RiderState

logger = logging.getLogger(__name__)


def init_system(config_path=None):
    """Initialise global state and return a SystemManager."""
    globalvar._init()
    config = Configuration(config_path)
    globalvar.set_value("config", config.as_dict())
    globalvar.set_value("funds", config.initial_funds)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_history", [])
    Order.reset_counter()
    return SystemManager(config)


class SystemManager:
    """Manages funds, riders, simulated time and the command loop."""

    def __init__(self, config=None):
        self.config = config or Configuration()
        self.grid_map = GridMap()
        self.planner = PathPlanner()
        self.order_manager = OrderManager(self.planner)
        self.display = DisplayManager()
        self.input_manager = InputManager()

    # ---------------------------------------------------------- properties
    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        r = globalvar.get_value("riders")
        if r is None:
            r = []
            globalvar.set_value("riders", r)
        return r

    @property
    def rider_id_counter(self):
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0)

    @property
    def recruitment_cost(self):
        return self.config.recruitment_cost

    # ----------------------------------------------------------- simulation
    def tick(self):
        """Advance the simulation by one tick. Returns new log entries."""
        globalvar.set_value("tick", self.current_tick + 1)
        self.order_manager.retry_unassigned()
        events = []
        for r in list(self.riders):
            n = len(r.log)
            try:
                r.move()
            except Exception:  # pragma: no cover - recovery path
                logger.exception("Rider %d failed; resetting", r.rider_id)
                self._recover_rider(r)
            for e in r.log[n:]:
                events.append((r.rider_id, e))
        return events

    @staticmethod
    def _recover_rider(rider):
        order = rider.current_order
        if order is not None and order.status != "completed":
            order.status = "assigned"
        rider.current_order = None
        rider.route = []
        rider.state = RiderState.IDLE

    def all_idle(self):
        return all(r.is_available() for r in self.riders) and not any(
            o.status == "unassigned" for o in self.order_manager.orders())

    def check_consistency(self):
        """Repair inconsistent rider states. Returns number of fixes."""
        fixes = 0
        for r in self.riders:
            if r.state != RiderState.IDLE and r.current_order is None:
                r.state = RiderState.IDLE
                r.route = []
                fixes += 1
        return fixes

    # ---------------------------------------------------------- persistence
    def save_state(self, path=None):
        path = path or self.config.values.get("state_file")
        data = {
            "system": self.config.as_dict(),
            "funds": self.funds,
            "tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "order_id_counter": Order._id_counter,
            "riders": [r.to_dict() for r in self.riders],
            "orders": list(globalvar.get_value("order_history") or [])
            + [o.to_dict() for o in self.order_manager.orders()],
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except OSError as exc:
            logger.error("Could not save state: %s", exc)
            return None
        return path

    def load_state(self, path=None):
        """Restore funds, time, riders (idle) and order history."""
        path = path or self.config.values.get("state_file")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            logger.warning("Could not load state: %s", exc)
            return False
        try:
            globalvar.set_value("funds", int(data.get("funds", self.funds)))
            globalvar.set_value("tick", int(data.get("tick", 0)))
            globalvar.set_value("rider_id_counter", int(data.get("rider_id_counter", 0)))
            Order.reset_counter(int(data.get("order_id_counter", 0)))
            riders = []
            for rd in data.get("riders", []):
                r = Rider(rd["rider_id"], rd.get("x"), rd.get("y"), rd.get("speed"))
                r.completed_orders = list(rd.get("completed_orders", []))
                r.distance_travelled = int(rd.get("distance_travelled", 0))
                riders.append(r)
            globalvar.set_value("riders", riders)
            globalvar.set_value("order_history",
                                [o for o in data.get("orders", []) if isinstance(o, dict)])
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Corrupt state file: %s", exc)
            return False
        return True

    # ------------------------------------------------------------- commands
    def handle_command(self, line, prompt_func=input):
        """Process one input line. Returns output text."""
        try:
            cmd, args = self.input_manager.parse_command(line)
        except InputError as exc:
            return "Error: %s" % exc
        if cmd == "":
            return ""
        if cmd is None:
            return "Unknown command. Type 'help' for the list of commands."
        try:
            if cmd == "start":
                return self.cmd_start(args, prompt_func)
            if cmd == "status":
                return (self.display.format_status(self.funds, self.current_tick, self.riders)
                        + "\n" + self.display.render_map(self.riders,
                                                         self.order_manager.orders()))
            if cmd == "orders":
                return self.display.format_orders(
                    self.order_manager.orders(),
                    globalvar.get_value("order_history") or [])
            if cmd == "riders":
                return self.display.format_rider_logs(self.riders)
            if cmd == "map":
                routes = [(r.position, r.route) for r in self.riders if r.route]
                return self.display.render_map(self.riders,
                                               self.order_manager.orders(), routes)
            if cmd == "tick":
                n = self.input_manager.parse_positive_int(args[0] if args else None, 1)
                return self.advance(n)
            if cmd == "run":
                limit = self.input_manager.parse_positive_int(args[0] if args else None, 1000)
                return self.run_until_idle(limit)
            if cmd == "save":
                path = self.save_state()
                return "State saved to %s" % path if path else "Save failed."
            if cmd == "history":
                return self.input_manager.format_history()
            if cmd == "help":
                return self.display.help_text()
            if cmd == "quit":
                globalvar.set_value("running", False)
                return "Goodbye."
        except (InputError, InvalidOrderError) as exc:
            return "Error: %s" % exc
        return ""

    def cmd_start(self, args, prompt_func=input):
        if args:
            coords = self.input_manager.parse_coordinates(args)
        else:
            try:
                text = prompt_func("Enter restaurant_x restaurant_y customer_x customer_y (0-800): ")
            except EOFError:
                return "Input cancelled."
            coords = self.input_manager.parse_coordinates(text)
        order, rider, new_rider = self.order_manager.create_order(coords)
        if rider is None:
            route = None
            wait = 0
        else:
            wait, pos = rider.workload(exclude=order)
            route = self.planner.plan_multi(pos, [order.res_pos, order.cus_pos], rider.speed)
        return self.display.format_route_info(order, rider, new_rider, route, wait,
                                              self.riders, self.order_manager.orders())

    @staticmethod
    def _format_events(events):
        return "\n".join("  t=%d rider %d: %s%s at (%d,%d)" % (
            e["time"], rid, e["event"],
            " (order #%d)" % e["order_id"] if e["order_id"] is not None else "",
            e["x"], e["y"]) for rid, e in events)

    def advance(self, n):
        events = []
        for _ in range(n):
            events.extend(self.tick())
        out = "Advanced %d tick(s); now at tick %d." % (n, self.current_tick)
        if events:
            out += "\n" + self._format_events(events)
        return out

    def run_until_idle(self, limit=1000):
        events = []
        count = 0
        while not self.all_idle() and count < limit:
            events.extend(self.tick())
            count += 1
        out = "Ran %d tick(s); now at tick %d.%s" % (
            count, self.current_tick,
            "" if self.all_idle() else " (limit reached)")
        if events:
            out += "\n" + self._format_events(events)
        return out

    def run(self):
        """Main loop: each iteration processes one command and one tick."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.running:
            try:
                line = input("[tick %d | funds %d] > " % (self.current_tick, self.funds))
            except (EOFError, KeyboardInterrupt):
                print()
                globalvar.set_value("running", False)
                break
            output = self.handle_command(line)
            if output:
                print(output)
            if self.running:
                events = self.tick()
                if events:
                    print(self._format_events(events))
                self.check_consistency()
        path = self.save_state()
        if path:
            print("State saved to %s" % path)
