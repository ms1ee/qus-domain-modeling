"""System manager: initialisation, recruitment, ticking and command loop."""

import json
import logging
import os

import globalvar
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from order_model import Order
from path_planner import GridMap, PathPlanner
from rider import Rider, RiderState, recruit_rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "funds": 1000,
    "recruitment_cost": 500,
    "recruitment_threshold": 300,
    "rider_speed": 20,
    "state_file": "dispatch_state.json",
}

HELP_TEXT = """Commands:
  start [rx ry cx cy]  (s/n)  create an order (restaurant + customer coords)
  status               (st)   system funds and rider status
  orders               (o)    all order details
  riders               (r)    rider status-change history
  map                  (m)    show the ASCII map
  tick [n]             (t)    advance n ticks (default 1)
  run                         advance until all orders are delivered
  history              (hist) show command history ('!!' repeats last)
  save [file] / load [file]   persist / restore state as JSON
  quit / exit          (q)    exit the program
Each command entered advances the simulation by one tick."""


def init_system(config=None):
    """Initialise the global system parameters."""
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    globalvar._init()
    globalvar.set_value("funds", int(cfg["funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("recruitment_cost", int(cfg["recruitment_cost"]))
    globalvar.set_value("recruitment_threshold", int(cfg["recruitment_threshold"]))
    globalvar.set_value("rider_speed", int(cfg["rider_speed"]))
    globalvar.set_value("state_file", cfg["state_file"])


def load_config(path):
    """Load a JSON configuration file; returns {} if missing/invalid."""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {k: v for k, v in data.items() if k in DEFAULT_CONFIG}
    except (OSError, ValueError) as exc:
        logger.warning("Could not read config %s: %s", path, exc)
        return {}


class SystemManager:
    """Core manager for funds, riders, orders and the main loop."""

    def __init__(self, config=None, config_path=None):
        cfg = load_config(config_path) if config_path else {}
        if config:
            cfg.update(config)
        init_system(cfg)
        self.grid_map = GridMap()
        self.path_planner = PathPlanner()
        self.order_manager = OrderManager()
        self.display_manager = DisplayManager()
        self.input_manager = InputManager()

    # ------------------------------------------------------------- properties
    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        return globalvar.get_value("riders", [])

    @property
    def running(self):
        return globalvar.get_value("running", False)

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0)

    @property
    def recruitment_cost(self):
        return globalvar.get_value("recruitment_cost", 500)

    @property
    def recruitment_threshold(self):
        return globalvar.get_value("recruitment_threshold", 300)

    # ------------------------------------------------------------ operations
    def idle_riders(self):
        return [r for r in self.riders if r.is_idle()]

    def maybe_recruit(self):
        """Recruit a rider if funds allow and orders outnumber idle riders."""
        pending = len(self.order_manager.pending_orders())
        if self.funds >= self.recruitment_threshold and pending > len(self.idle_riders()):
            return recruit_rider(self.recruitment_cost)
        return None

    def tick(self, n=1):
        """Advance the simulation by ``n`` ticks."""
        for _ in range(n):
            globalvar.set_value("tick", self.current_tick + 1)
            for r in self.riders:
                try:
                    r.move()
                except Exception:  # error recovery for a single rider
                    logger.exception("Rider %s failed to move", r.rider_id)
                    self._recover_rider(r)
            self.check_consistency()

    def _recover_rider(self, rider):
        rider.path = []
        if rider.current_order is not None and rider.current_order.status != "completed":
            rider.state = RiderState.PICKING_UP
            rider.path = rider._planner.plan(rider.x, rider.y, *rider.current_order.res_pos)
        else:
            rider.current_order = None
            rider.state = RiderState.IDLE

    def check_consistency(self):
        """Fix obvious inconsistencies between riders and orders."""
        for r in self.riders:
            if r.current_order is None and r.active_order_count == 0 \
                    and r.state != RiderState.IDLE:
                r.state = RiderState.IDLE
                r.path = []
            for o in r.orders:
                if o.rider_id is None:
                    o.rider_id = r.rider_id

    def run_until_done(self, limit=100000):
        count = 0
        while self.order_manager.pending_orders() and count < limit:
            self.tick()
            count += 1
        return count

    # ----------------------------------------------------------- persistence
    def save_state(self, path=None):
        path = path or globalvar.get_value("state_file", DEFAULT_CONFIG["state_file"])
        data = {
            "config": {
                "funds": self.funds,
                "recruitment_cost": self.recruitment_cost,
                "recruitment_threshold": self.recruitment_threshold,
                "rider_speed": globalvar.get_value("rider_speed", 20),
            },
            "tick": self.current_tick,
            "rider_id": globalvar.get_value("rider_id", 0),
            "order_id_counter": globalvar.get_value("order_id_counter", 0),
            "orders": [o.to_dict() for o in self.order_manager.orders],
            "riders": [r.to_dict() for r in self.riders],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return path

    def load_state(self, path=None):
        path = path or globalvar.get_value("state_file", DEFAULT_CONFIG["state_file"])
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        cfg = dict(data.get("config", {}))
        cfg["state_file"] = path
        init_system(cfg)
        globalvar.set_value("tick", data.get("tick", 0))
        globalvar.set_value("rider_id", data.get("rider_id", 0))
        globalvar.set_value("order_id_counter", data.get("order_id_counter", 0))
        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        globalvar.set_value("orders", orders)
        by_id = {o.id: o for o in orders}
        riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
        globalvar.set_value("riders", riders)
        return path

    # -------------------------------------------------------------- commands
    def handle_start(self, coords):
        values = self.input_manager.parse_coordinates(coords)
        order = self.order_manager.create_order(values)
        recruited = self.maybe_recruit()
        rider = self.order_manager.assign_order(order)
        points, length = rider.remaining_route()
        start = (rider.x, rider.y)
        route = self.path_planner.build_route(start, points, rider.speed)
        lines = [
            f"Order #{order.id} created at tick {order.start_time}",
            f"Restaurant grid position: {order.res_pos} "
            f"(cell {self.grid_map.cell_of(*order.res_pos)})",
            f"Customer grid position:   {order.cus_pos} "
            f"(cell {self.grid_map.cell_of(*order.cus_pos)})",
        ]
        if recruited is not None:
            lines.append(f"New rider added: Yes (Rider #{recruited.rider_id}, "
                         f"cost {self.recruitment_cost}, funds now {self.funds})")
        else:
            lines.append(f"New rider added: No (funds {self.funds})")
        lines.append(f"Assigned to Rider #{rider.rider_id} at ({rider.x},{rider.y}), "
                     f"active orders: {rider.active_order_count}")
        lines.append(f"Rider speed: {rider.speed} units/tick, route length: "
                     f"{route.length} units, estimated time: {route.estimated_time} ticks")
        lines.append("Route: " + " -> ".join(f"({p[0]},{p[1]})" for p in route.points()))
        shown = [o for o in rider.orders if o.status != "completed"]
        lines.append(self.display_manager.render_map([rider], shown, route.points()))
        return "\n".join(lines)

    def handle_command(self, line):
        """Execute a command line. Returns (output, advance_tick)."""
        cmd, args = self.input_manager.parse_command(line)
        if not cmd:
            return "", False
        if cmd == "start":
            if not args.strip():
                args = self.input_manager.read(
                    "Enter restaurant_x restaurant_y customer_x customer_y: ")
            return self.handle_start(args), True
        if cmd == "status":
            return self.display_manager.format_status(
                self.funds, self.current_tick, self.riders), True
        if cmd == "orders":
            return self.display_manager.format_orders(self.order_manager.orders), True
        if cmd == "riders":
            return self.display_manager.format_rider_logs(self.riders), True
        if cmd == "map":
            return self.display_manager.render_map(
                self.riders, self.order_manager.pending_orders()), True
        if cmd == "tick":
            n = self.input_manager.parse_positive_int(args, 1)
            self.tick(n)
            return f"Advanced {n} tick(s). Now at tick {self.current_tick}.", False
        if cmd == "run":
            n = self.run_until_done()
            return f"Advanced {n} tick(s); all orders handled. Tick {self.current_tick}.", False
        if cmd == "history":
            return "\n".join(f"{i + 1}: {c}" for i, c in
                             enumerate(self.input_manager.command_history)), False
        if cmd == "save":
            return f"State saved to {self.save_state(args.strip() or None)}", False
        if cmd == "load":
            return f"State loaded from {self.load_state(args.strip() or None)}", False
        if cmd == "help":
            return HELP_TEXT, False
        if cmd == "quit":
            self.running = False
            return "Goodbye.", False
        return f"Unknown command '{cmd}'. Type 'help' for a list of commands.", False

    def run(self):
        """Main loop: each iteration is one simulated tick."""
        print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
        while self.running:
            try:
                line = self.input_manager.read(f"[t={self.current_tick}] > ")
                output, advance = self.handle_command(line)
                if output:
                    print(output)
                if advance and self.running:
                    self.tick()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                self.running = False
            except ValueError as exc:
                print(f"Input error: {exc}")
            except Exception as exc:  # graceful recovery
                logger.exception("Unexpected error")
                print(f"Error: {exc}. System state recovered.")
                self.check_consistency()
