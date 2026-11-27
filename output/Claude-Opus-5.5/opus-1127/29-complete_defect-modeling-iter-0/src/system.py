"""System manager: funds, riders, simulated time and command loop."""

import json
import logging

import globalvar
from config import Configuration
from display import DisplayManager
from grid_map import GridMap
from input_manager import InputError, InputManager
from order import OrderManager
from order_model import Order
from path_planner import PathPlanner
from rider import IDLE, Rider

logger = logging.getLogger(__name__)


def init_system(config=None):
    """Initialise all global system parameters."""
    cfg = config if config is not None else Configuration()
    globalvar._init()
    globalvar.set_value("config", cfg)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", int(cfg.get("initial_funds", 300)))
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("pending_orders", [])
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("grid_map", GridMap(int(cfg.get("map_size", 800)),
                                            int(cfg.get("map_size", 800)),
                                            int(cfg.get("cell_size", 100))))


class SystemManager:
    """Core class managing funds, riders, time and user commands."""

    def __init__(self, config=None):
        self.config = config if config is not None else Configuration()
        init_system(self.config)
        cs = int(self.config.get("cell_size", 100))
        ms = int(self.config.get("map_size", 800))
        self.grid_map = globalvar.get_value("grid_map")
        self.order_manager = OrderManager(PathPlanner(cs, ms))
        self.display = DisplayManager(ms, cs)
        self.input_manager = InputManager(int(self.config.get("max_history", 500)))
        self.last_route = None

    # properties ------------------------------------------------------------
    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        return globalvar.get_value("riders") or []

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0)

    # funds & riders --------------------------------------------------------
    def add_funds(self, amount):
        globalvar.set_value("funds", int(self.funds + amount))

    def recruit_rider(self):
        """Create a new rider with an auto-incremented id."""
        counter = (globalvar.get_value("rider_id_counter", 0) or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        riders = self.riders
        riders.append(rider)
        globalvar.set_value("riders", riders)
        logger.info("Recruited rider %d", counter)
        return rider

    def check_recruitment(self):
        """Recruit a rider automatically when funds >= threshold."""
        threshold = int(self.config.get("recruit_threshold", 300))
        cost = int(self.config.get("recruit_cost", threshold))
        max_riders = int(self.config.get("max_riders", 50))
        if self.funds >= threshold and len(self.riders) < max_riders:
            rider = self.recruit_rider()
            self.add_funds(-cost)
            return rider
        return None

    def remove_rider(self, rider_id):
        """Remove an idle rider; its orders go back to the pending queue."""
        for rider in list(self.riders):
            if rider.rider_id == rider_id:
                for o in rider.active_orders():
                    o.rider_id = None
                    o.status = "pending"
                    self.order_manager.pending_orders().append(o)
                self.riders.remove(rider)
                return True
        return False

    # orders ----------------------------------------------------------------
    def place_order(self, rx, ry, cx, cy):
        """Create an order, collect its fee, recruit if possible, assign it."""
        order = self.order_manager.create_order(rx, ry, cx, cy)
        self.add_funds(order.fee)
        recruited = self.check_recruitment()
        rider = self.order_manager.assign_order(order)
        route = self.order_manager.planned_route_for(rider, order) if rider else None
        self.last_route = (rider, route) if rider else None
        return {"order": order, "recruited": recruited, "rider": rider,
                "route": route}

    # time ------------------------------------------------------------------
    def advance_tick(self):
        """Advance the simulation by one tick; returns new log entries."""
        tick = self.current_tick + 1
        globalvar.set_value("tick", tick)
        try:
            self.order_manager.assign_pending()
        except Exception:
            logger.exception("Assignment failed; recovering")
            self.check_consistency()
        events = []
        for rider in list(self.riders):
            before = len(rider.log)
            try:
                rider.move()
            except Exception:
                logger.exception("Rider %d failed to move; recovering",
                                 rider.rider_id)
                self.check_consistency()
            for entry in rider.log[before:] if len(rider.log) >= before else []:
                events.append((rider.rider_id, entry))
        return events

    def check_consistency(self):
        """Repair inconsistent state; returns list of fixes applied."""
        fixes = []
        if not isinstance(self.funds, int):
            globalvar.set_value("funds", int(self.funds or 0))
            fixes.append("funds type")
        ms = int(self.config.get("map_size", 800))
        pending = self.order_manager.pending_orders()
        for o in list(pending):
            if o.status == "completed" or o.rider_id is not None:
                pending.remove(o)
                fixes.append("pending order %d" % o.id)
        for r in self.riders:
            r.x = max(0, min(ms, int(r.x)))
            r.y = max(0, min(ms, int(r.y)))
            r.orders = [o for o in r.orders if o.status != "completed"]
            if r.state != IDLE and (r.current_order is None or
                                    r.current_order not in r.orders):
                r.state = IDLE
                r.current_order = None
                r.path = []
                r.target = None
                fixes.append("rider %d reset" % r.rider_id)
        for f in fixes:
            logger.warning("Consistency fix: %s", f)
        return fixes

    # persistence -----------------------------------------------------------
    def save_state(self, path=None):
        path = path or self.config.get("state_file", "dispatch_state.json")
        data = {
            "config": self.config.to_dict(),
            "funds": self.funds, "tick": self.current_tick,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "order_id_counter": globalvar.get_value("order_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.all_orders()],
            "pending_orders": [o.id for o in self.order_manager.pending_orders()],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return path

    def load_state(self, path=None):
        path = path or self.config.get("state_file", "dispatch_state.json")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        init_system(self.config)
        globalvar.set_value("tick", int(data.get("tick", 0)))
        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        by_id = {o.id: o for o in orders}
        globalvar.set_value("orders", orders)
        globalvar.set_value("pending_orders",
                            [by_id[i] for i in data.get("pending_orders", [])
                             if i in by_id])
        riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
        globalvar.set_value("riders", riders)
        globalvar.set_value("funds", int(data.get("funds", 0)))
        globalvar.set_value("rider_id_counter", int(data.get("rider_id_counter",
                                                             len(riders))))
        globalvar.set_value("order_id_counter",
                            max([int(data.get("order_id_counter", 0))] +
                                [o.id for o in orders]))
        self.check_consistency()
        return path

    # commands --------------------------------------------------------------
    def handle_command(self, line):
        """Process one command; returns True if time should advance."""
        try:
            cmd, args = self.input_manager.parse(line)
        except InputError as exc:
            print("Error: %s" % exc)
            return False
        if not cmd:
            return False
        handlers = {
            "start": self.cmd_start, "status": self.cmd_status,
            "orders": self.cmd_orders, "riders": self.cmd_riders,
            "map": self.cmd_map, "tick": self.cmd_tick,
            "history": self.cmd_history, "save": self.cmd_save,
            "load": self.cmd_load, "help": self.cmd_help, "quit": self.cmd_quit,
        }
        handler = handlers.get(cmd)
        if handler is None:
            print("Unknown command '%s'. Type 'help' for the list." % cmd)
            return False
        try:
            return handler(args)
        except InputError as exc:
            print("Error: %s" % exc)
        except (OSError, ValueError, KeyError) as exc:
            print("Error: %s" % exc)
        except Exception as exc:  # pragma: no cover - recovery path
            logger.exception("Command failed")
            fixes = self.check_consistency()
            print("Unexpected error (%s); state recovered (%d fixes)."
                  % (exc, len(fixes)))
        return False

    def cmd_start(self, args):
        if args:
            coords = self.input_manager.validate_coordinates(args)
        else:
            try:
                coords = self.input_manager.prompt_coordinates()
            except EOFError:
                raise InputError("no coordinates given")
        result = self.place_order(*coords)
        order = result["order"]
        print("Order #%d created (fee %d, funds now %d)"
              % (order.id, order.fee, self.funds))
        print("  Restaurant: input (%d,%d) -> grid %s center (%d,%d)"
              % (order.raw_restaurant + order.restaurant_grid + order.restaurant))
        print("  Customer:   input (%d,%d) -> grid %s center (%d,%d)"
              % (order.raw_customer + order.customer_grid + order.customer))
        rec = result["recruited"]
        print("  New rider added: %s" % ("yes (rider %d)" % rec.rider_id
                                         if rec else "no"))
        rider, route = result["rider"], result["route"]
        if rider is None:
            print("  No rider available; order is waiting in the queue.")
        else:
            print("  Assigned to rider %d" % rider.rider_id)
            print(self.display.format_route(rider, route))
            print(self.display.render_map(self.riders, [order], route))
        return True

    def cmd_status(self, args):
        print(self.display.format_status(self.funds, self.current_tick,
                                         self.riders,
                                         self.order_manager.pending_orders()))
        return True

    def cmd_orders(self, args):
        print(self.display.format_orders(self.order_manager.all_orders()))
        return True

    def cmd_riders(self, args):
        print(self.display.format_rider_logs(self.riders))
        return True

    def cmd_map(self, args):
        active = [o for o in self.order_manager.all_orders()
                  if o.status != "completed"]
        print(self.display.render_map(self.riders, active))
        return True

    def cmd_tick(self, args):
        n = 1
        if args:
            try:
                n = int(args[0])
            except ValueError:
                raise InputError("tick count must be an integer")
            if not 1 <= n <= 100000:
                raise InputError("tick count must be between 1 and 100000")
        for _ in range(n):
            self._print_events(self.advance_tick())
        print("Time is now tick %d." % self.current_tick)
        return False

    def cmd_history(self, args):
        for i, line in enumerate(self.input_manager.command_history, 1):
            print("%4d  %s" % (i, line))
        return False

    def cmd_save(self, args):
        path = self.save_state(args[0] if args else None)
        print("State saved to %s" % path)
        return False

    def cmd_load(self, args):
        path = self.load_state(args[0] if args else None)
        print("State loaded from %s" % path)
        return False

    def cmd_help(self, args):
        print(self.input_manager.help_text())
        return False

    def cmd_quit(self, args):
        self.running = False
        if self.config.get("autosave_on_exit", True):
            try:
                path = self.save_state()
                print("State saved to %s" % path)
            except OSError as exc:
                print("Could not save state: %s" % exc)
        print("Goodbye.")
        return False

    @staticmethod
    def _print_events(events):
        for rider_id, e in events:
            if e.get("event") == "spawn":
                continue
            print("  [t=%s] rider %d %s order #%s at (%d,%d)"
                  % (e.get("time"), rider_id, e.get("event"), e.get("order_id"),
                     e.get("x", 0), e.get("y", 0)))

    def run(self, reader=input):
        """Main loop: every processed command is one simulated tick."""
        print("Food Delivery Dispatch Simulator - type 'help' for commands.")
        while self.running:
            try:
                line = reader("[tick %d | funds %d] > " % (self.current_tick,
                                                          self.funds))
            except (EOFError, KeyboardInterrupt):
                print()
                line = "quit"
            if self.handle_command(line) and self.running:
                self._print_events(self.advance_tick())
