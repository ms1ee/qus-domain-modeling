"""System manager: funds, riders, simulated time and persistence."""

import json
import logging

import globalvar
from config import Configuration
from gridmap import GridMap
from order import OrderManager
from order_model import Order
from path_planner import PathPlanner
from rider import Rider, IDLE, DELIVERING

logger = logging.getLogger(__name__)


def get_config():
    cfg = globalvar.get_value("config")
    if cfg is None:
        cfg = Configuration()
        globalvar.set_value("config", cfg)
    return cfg


def recruit_rider():
    """Create a new rider, deduct the recruitment cost and register it."""
    cfg = get_config()
    counter = (globalvar.get_value("rider_id_counter", 0) or 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    globalvar.set_value("funds", (globalvar.get_value("funds", 0) or 0)
                        - cfg.get("recruitment_cost"))
    rider = Rider(counter, cfg.get("rider_start_x"), cfg.get("rider_start_y"),
                  cfg.get("rider_speed"))
    riders = globalvar.get_value("riders", None)
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    riders.append(rider)
    logger.info("Recruited rider %s", counter)
    return rider


def init_system(config=None):
    """Initialise the global system state and return a SystemManager."""
    globalvar._init()
    cfg = config if isinstance(config, Configuration) else Configuration(config)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", cfg.get("initial_funds"))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    return SystemManager()


class SystemManager:
    """Facade over the global system state."""

    def __init__(self):
        self.config = get_config()
        self.grid_map = GridMap(self.config.get("map_size"),
                                self.config.get("map_size"),
                                self.config.get("cell_size"))
        self.path_planner = PathPlanner(self.config.get("cell_size"), self.grid_map)
        self.order_manager = OrderManager(self)
        self.recruitment_cost = self.config.get("recruitment_cost")

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        return globalvar.get_value("riders", [])

    @property
    def orders(self):
        return globalvar.get_value("orders", [])

    @property
    def rider_id_counter(self):
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def running(self):
        return globalvar.get_value("running", False)

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0)

    def recruit_rider(self):
        return recruit_rider()

    def advance(self, ticks=1):
        """Advance the simulation by ``ticks`` units of time."""
        for _ in range(max(0, int(ticks))):
            globalvar.set_value("tick", self.current_tick + 1)
            for rider in self.riders:
                try:
                    rider.move()
                except Exception as exc:  # pragma: no cover - recovery
                    logger.exception("Rider %s failed to move: %s",
                                     rider.rider_id, exc)
                    self.check_consistency()

    def all_delivered(self):
        return all(o.status == "completed" for o in self.orders
                   if o.rider_id is not None)

    def check_consistency(self):
        """Repair inconsistent state; returns a list of fixes made."""
        fixes = []
        if not isinstance(globalvar.get_value("riders"), list):
            globalvar.set_value("riders", [])
            fixes.append("riders list reset")
        if not isinstance(globalvar.get_value("orders"), list):
            globalvar.set_value("orders", [])
            fixes.append("orders list reset")
        size = self.config.get("map_size")
        for r in self.riders:
            if not (0 <= r.x <= size and 0 <= r.y <= size):
                r.x, r.y = max(0, min(size, r.x)), max(0, min(size, r.y))
                r.route_points = None
                fixes.append("rider %s clamped into map" % r.rider_id)
            if r.state != IDLE and not r.active_orders:
                r.state = IDLE
                fixes.append("rider %s set idle" % r.rider_id)
            if r.state == IDLE and r.active_orders:
                r.route_points = None
        for o in self.orders:
            if o.status not in ("completed", "pending") and o.rider_id is None:
                o.status = "pending"
                fixes.append("order %s reset to pending" % o.id)
        return fixes

    # -------------------------------------------------------------- persistence
    def save_state(self, path=None):
        path = path or self.config.get("state_file")
        data = {
            "system": self.config.values,
            "state": {"funds": self.funds, "rider_id_counter": self.rider_id_counter,
                      "tick": self.current_tick},
            "orders": [o.to_dict() for o in self.orders],
            "riders": [r.to_dict() for r in self.riders],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return path

    def load_state(self, path=None):
        path = path or self.config.get("state_file")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        st = data.get("state", {})
        globalvar.set_value("funds", st.get("funds", self.funds))
        globalvar.set_value("rider_id_counter", st.get("rider_id_counter", 0))
        globalvar.set_value("tick", st.get("tick", 0))
        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        by_id = {o.id: o for o in orders}
        riders = []
        for d in data.get("riders", []):
            r = Rider(d["rider_id"], d["x"], d["y"], d.get("speed", 20))
            r.state = d.get("state", IDLE)
            r.special_case = d.get("special_case", False)
            r.orders = [by_id[i] for i in d.get("orders", []) if i in by_id]
            r.log = d.get("log", r.log)
            r.total_distance = d.get("total_distance", 0)
            if r.state == DELIVERING and r.current_order is not None:
                r.current_order.status = "delivering"
            riders.append(r)
        globalvar.set_value("orders", orders)
        globalvar.set_value("riders", riders)
        self.check_consistency()
        return path
