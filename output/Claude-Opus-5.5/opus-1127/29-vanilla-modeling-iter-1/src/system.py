"""System manager and initialisation."""

import json
import logging

import globalvar
from config import Configuration
from order import OrderManager
from order_model import Order
from path_planner import GridMap, PathPlanner
from rider import Rider, RiderState

logger = logging.getLogger(__name__)


class SystemManager:
    """Core manager of funds, riders, time and orders (state in globalvar)."""

    def __init__(self, config=None):
        self.config = config or globalvar.get_value("config") or Configuration()
        self.recruitment_cost = self.config.recruitment_cost
        self.grid_map = GridMap()
        self.order_manager = OrderManager(self)

    # -------------------------------------------------------------- properties
    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", value)

    @property
    def riders(self):
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def rider_id_counter(self):
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def is_running(self):
        return globalvar.get_value("running", False)

    @is_running.setter
    def is_running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0)

    # ----------------------------------------------------------------- riders
    def recruit_rider(self):
        """Hire a rider if funds allow. Returns the rider or None."""
        if self.funds < self.recruitment_cost:
            return None
        self.funds = self.funds - self.recruitment_cost
        new_id = self.rider_id_counter + 1
        globalvar.set_value("rider_id_counter", new_id)
        rider = Rider(new_id, self.config.initial_rider_x,
                      self.config.initial_rider_y, self.config.default_speed)
        self.riders.append(rider)
        logger.info("Recruited rider %d", new_id)
        return rider

    def idle_rider_count(self):
        """Number of idle riders with no queued orders."""
        return sum(1 for r in self.riders if r.is_idle())

    def check_recruitment(self):
        """Recruit while funds >= cost and pending orders > idle riders."""
        added = []
        while (self.funds >= self.recruitment_cost and
               len(self.order_manager.pending_orders()) > self.idle_rider_count()):
            rider = self.recruit_rider()
            if rider is None:
                break
            added.append(rider)
        return added

    def get_rider(self, rider_id):
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    # ----------------------------------------------------------------- orders
    def place_order(self, coords):
        """Create and assign an order.

        Returns:
            dict with keys order, new_riders, rider, route.
        """
        order = self.order_manager.create_order(coords)
        new_riders = self.check_recruitment()
        rider = self.order_manager.assign_order(order)
        route = None
        if rider is not None:
            route = PathPlanner.plan_multi(rider.position,
                                           [order.res_pos, order.cus_pos],
                                           rider.speed)
        return {"order": order, "new_riders": new_riders,
                "rider": rider, "route": route}

    # ------------------------------------------------------------------- time
    def tick(self, n=1):
        """Advance the simulation by ``n`` ticks."""
        for _ in range(max(int(n), 0)):
            globalvar.set_value("tick", self.current_tick + 1)
            try:
                self.check_recruitment()
                self.order_manager.assign_pending()
                for r in list(self.riders):
                    r.move()
            except Exception as exc:  # error recovery
                logger.exception("Error during tick: %s", exc)
            self.consistency_check()

    def consistency_check(self):
        """Repair obviously inconsistent rider states."""
        for r in self.riders:
            if r.state != RiderState.IDLE and not r.orders:
                logger.warning("Rider %s inconsistent, resetting", r.rider_id)
                r.state = RiderState.IDLE
            r.x = min(max(r.x, 0), 800)
            r.y = min(max(r.y, 0), 800)

    def stop(self):
        self.is_running = False

    # ------------------------------------------------------------ persistence
    def save_state(self, path):
        """Save config, riders and orders to a JSON file."""
        data = {
            "config": self.config.to_dict(),
            "funds": self.funds,
            "tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.orders],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return path

    def load_state(self, path):
        """Load state written by ``save_state``."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.config = Configuration.from_dict(data.get("config", {}), path)
        self.recruitment_cost = self.config.recruitment_cost
        globalvar.set_value("config", self.config)
        globalvar.set_value("funds", int(data.get("funds", 0)))
        globalvar.set_value("tick", int(data.get("tick", 0)))
        globalvar.set_value("rider_id_counter", int(data.get("rider_id_counter", 0)))
        orders = [Order.from_dict(o) for o in data.get("orders", [])]
        Order.reset_ids(max([o.id for o in orders] + [0]) + 1)
        globalvar.set_value("orders", orders)
        by_id = {o.id: o for o in orders}
        riders = []
        for rd in data.get("riders", []):
            r = Rider(rd["rider_id"], rd["x"], rd["y"], rd["speed"])
            r.state = int(rd.get("state", 0))
            r.special_case = bool(rd.get("special_case", False))
            r.orders = [by_id[i] for i in rd.get("orders", []) if i in by_id]
            r.log = list(rd.get("log", []))
            riders.append(r)
        globalvar.set_value("riders", riders)


def init_system(config_path=None):
    """Initialise global state and return a SystemManager.

    Funds 1000, empty rider list, rider id counter 0, running True, tick 0.
    """
    globalvar._init()
    config = Configuration.load(config_path)
    globalvar.set_value("config", config)
    globalvar.set_value("funds", config.initial_funds)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    Order.reset_ids()
    manager = SystemManager(config)
    globalvar.set_value("system", manager)
    return manager
