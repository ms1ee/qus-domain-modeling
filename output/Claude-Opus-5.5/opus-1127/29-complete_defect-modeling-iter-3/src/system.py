"""System management: funds, riders, simulated time and persistence."""

import json
import logging

import globalvar
from config import Configuration
from grid_map import GridMap
from order import OrderManager, find_best_rider_for_order
from order_model import Order, OrderStatus
from path_planner import PathPlanner
from rider import Rider, RiderState

logger = logging.getLogger(__name__)


class SystemManager:
    """Core manager for funds, riders and the simulation clock.

    State is stored in :mod:`globalvar` so all modules share it.
    """

    def __init__(self, config=None):
        self.config = config or Configuration()
        self.order_manager = OrderManager()
        self.grid_map = GridMap()
        self.planner = PathPlanner(self.grid_map)

    # Shared state properties ------------------------------------------
    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

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
    def running(self):
        return globalvar.get_value("running", False)

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def current_time(self):
        return globalvar.get_value("time", 0)

    @property
    def orders(self):
        return self.order_manager.orders

    # Riders -------------------------------------------------------------
    def add_rider(self, x=None, y=None, speed=None):
        """Create a new rider with an auto-incremented id."""
        rider_id = self.rider_id_counter + 1
        globalvar.set_value("rider_id_counter", rider_id)
        rider = Rider(rider_id, x, y, speed)
        self.riders.append(rider)
        logger.info("Rider #%d created", rider_id)
        return rider

    def remove_rider(self, rider_id):
        """Remove an idle rider without pending orders. Returns True on success."""
        for r in self.riders:
            if r.rider_id == rider_id:
                if r.state != RiderState.IDLE or r.has_pending_orders():
                    return False
                self.riders.remove(r)
                return True
        return False

    def get_rider(self, rider_id):
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    def recruit_if_possible(self):
        """Recruit a rider when funds reach the threshold. Returns it or None."""
        if (self.funds >= self.config.recruit_threshold
                and self.funds >= self.config.rider_recruit_cost
                and len(self.riders) < self.config.max_riders):
            self.funds = self.funds - self.config.rider_recruit_cost
            return self.add_rider()
        return None

    # Orders -------------------------------------------------------------
    def place_order(self, coords):
        """Create and dispatch an order.

        Returns a dict with keys ``order``, ``rider``, ``new_rider`` and
        ``route``.
        """
        order = self.order_manager.create_order(coords)
        self.funds = self.funds + self.config.order_income
        new_rider = self.recruit_if_possible()
        rider = find_best_rider_for_order(order)
        route = None
        if rider is not None:
            _, start = rider.remaining_work()
            self.order_manager.assign_to_rider(order, rider)
            route = self.planner.plan_multi(start, [order.res_pos,
                                                    order.cus_pos],
                                            rider.speed)
        return {"order": order, "rider": rider, "new_rider": new_rider,
                "route": route}

    # Simulation ---------------------------------------------------------
    def tick(self, count=1):
        """Advance the simulation ``count`` ticks; returns event descriptions."""
        events = []
        for _ in range(max(0, int(count))):
            globalvar.set_value("time", self.current_time + 1)
            new_rider = self.recruit_if_possible()
            if new_rider is not None:
                events.append("t=%d: new rider #%d recruited"
                              % (self.current_time, new_rider.rider_id))
            for order, rider in self.order_manager.dispatch_pending():
                events.append("t=%d: pending order #%d assigned to rider #%d"
                              % (self.current_time, order.id, rider.rider_id))
            for rider in list(self.riders):
                before = len(rider.log)
                try:
                    rider.move()
                except Exception:  # pragma: no cover - recovery path
                    logger.exception("Rider #%d failed to move", rider.rider_id)
                    self.check_consistency(repair=True)
                for entry in rider.log[before:]:
                    events.append("t=%d: rider #%d %s (order #%s) at (%d,%d)"
                                  % (entry["time"], rider.rider_id,
                                     entry["event"], entry["order_id"],
                                     entry["x"], entry["y"]))
        return events

    def check_consistency(self, repair=True):
        """Check (and optionally repair) system state. Returns issue list."""
        issues = []
        if not isinstance(self.funds, int):
            issues.append("funds not an integer")
            if repair:
                try:
                    self.funds = int(self.funds)
                except (TypeError, ValueError):
                    self.funds = 0
        rider_ids = set()
        for r in self.riders:
            rider_ids.add(r.rider_id)
            if r.state not in (0, 1, 2):
                issues.append("rider #%d invalid state" % r.rider_id)
                if repair:
                    r.reset_to_idle()
            if r.state != RiderState.IDLE and (
                    r.current_order is None
                    or r.current_order.status == OrderStatus.COMPLETED):
                issues.append("rider #%d busy without active order"
                              % r.rider_id)
                if repair:
                    r.reset_to_idle()
            done = [o for o in r.orders if o.status == OrderStatus.COMPLETED]
            if done:
                issues.append("rider #%d holds completed orders" % r.rider_id)
                if repair:
                    for o in done:
                        r.orders.remove(o)
        held = {id(o) for r in self.riders for o in r.orders}
        for o in self.orders:
            if o.status == OrderStatus.COMPLETED:
                continue
            if o.rider_id is not None and (o.rider_id not in rider_ids
                                           or id(o) not in held):
                issues.append("order #%d assigned to missing rider" % o.id)
                if repair:
                    o.rider_id = None
                    o.status = OrderStatus.PENDING
        return issues

    # Persistence --------------------------------------------------------
    def save_state(self, path=None):
        """Save configuration, riders and order history to JSON."""
        path = path or self.config.data_file
        data = {
            "config": self.config.to_dict(),
            "funds": self.funds,
            "time": self.current_time,
            "rider_id_counter": self.rider_id_counter,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.orders],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return path

    def load_state(self, path=None):
        """Load state from a JSON file previously written by save_state."""
        path = path or self.config.data_file
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for key, value in data.get("config", {}).items():
            if key in Configuration.DEFAULTS:
                self.config.values[key] = value
        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        by_id = {o.id: o for o in orders}
        globalvar.set_value("orders", orders)
        globalvar.set_value("funds", int(data.get("funds", 0)))
        globalvar.set_value("time", int(data.get("time", 0)))
        globalvar.set_value("rider_id_counter",
                            int(data.get("rider_id_counter", 0)))
        globalvar.set_value("riders", [Rider.from_dict(d, by_id)
                                       for d in data.get("riders", [])])
        Order.reset_counter(max(by_id) + 1 if by_id else 1)
        self.check_consistency(repair=True)
        return path


def init_system(config=None):
    """Initialise global system state and return a SystemManager.

    Sets: riders=[], rider_id_counter=0, running=True, funds, time=0,
    orders=[].
    """
    if config is None:
        config = Configuration()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", int(config.initial_funds))
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("config", config)
    globalvar.set_value("default_speed", int(config.default_speed))
    globalvar.set_value("spawn_position", (int(config.spawn_x),
                                           int(config.spawn_y)))
    globalvar.set_value("delivery_bonus", int(config.delivery_bonus))
    Order.reset_counter()
    manager = SystemManager(config)
    globalvar.set_value("system", manager)
    return manager
