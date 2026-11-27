"""System manager: funds, riders, time and persistence."""

import json
import logging

import globalvar
from config import Configuration
from grid_map import GridMap
from order import OrderManager
from path_planner import PathPlanner
from rider import Rider

logger = logging.getLogger(__name__)


class SystemManager:
    """Core manager of funds, riders and system state (stored in globalvar)."""

    def __init__(self, config=None):
        self.config = config or Configuration()
        self.order_manager = OrderManager()
        self.planner = PathPlanner()

    # -------------------------------------------------------------- properties
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
    def orders(self):
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0) or 0

    @property
    def grid_map(self):
        return globalvar.get_value("grid_map")

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    # ------------------------------------------------------------------ riders
    def recruit_rider(self, force=False):
        """Create a new rider (paying the recruitment cost)."""
        if not force and len(self.riders) >= int(self.config.get("max_riders")):
            return None
        counter = (globalvar.get_value("rider_id_counter", 0) or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter, x=int(self.config.get("spawn_x")),
                      y=int(self.config.get("spawn_y")),
                      speed=int(self.config.get("rider_speed")))
        self.funds = self.funds - int(self.config.get("recruitment_cost"))
        self.riders.append(rider)
        logger.info("Recruited rider %d", counter)
        return rider

    def check_recruitment(self):
        """Recruit a rider automatically when funds reach the threshold."""
        if self.funds >= self.config.recruitment_threshold and \
                len(self.riders) < int(self.config.get("max_riders")):
            return self.recruit_rider()
        return None

    def get_rider(self, rider_id):
        """Find a rider by id."""
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    # ------------------------------------------------------------------ orders
    def process_order(self, coords):
        """Create and dispatch an order.

        Returns a dict with keys: order, rider, new_rider, route, wait_time.
        """
        new_riders = []
        if not self.riders:
            r = self.recruit_rider(force=True)
            if r:
                new_riders.append(r)
        r = self.check_recruitment()
        if r:
            new_riders.append(r)
        order = self.order_manager.create_order(coords)
        from order import find_best_rider_for_order
        rider = find_best_rider_for_order(order, self.riders)
        if rider is None:
            raise RuntimeError("No rider available")
        start, committed = rider.projected_end()
        self.order_manager.assign(order, rider)
        route = self.planner.plan_route(start, [order.res_pos, order.cus_pos],
                                        rider.speed, order.id)
        speed = rider.speed if rider.speed > 0 else 1
        wait = -(-committed // speed)
        return {
            "order": order,
            "rider": rider,
            "new_rider": bool(new_riders),
            "new_riders": new_riders,
            "route": route,
            "wait_time": wait,
            "total_time": wait + route.estimated_time,
        }

    # -------------------------------------------------------------------- time
    def tick(self, n=1):
        """Advance the simulation by ``n`` ticks."""
        for _ in range(max(0, int(n))):
            globalvar.set_value("tick", self.current_tick + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception as exc:
                    logger.error("Rider %s failed to move: %s; recovering",
                                 rider.rider_id, exc)
                    rider.reset()
            earned = self.order_manager.settle_completed(
                int(self.config.get("order_revenue")))
            if earned:
                self.funds = self.funds + earned
            self.check_recruitment()

    def run_until_idle(self, limit=10000):
        """Advance until all orders are complete (or ``limit`` ticks)."""
        ticks = 0
        while ticks < limit and any(o.status != "completed" for o in self.orders):
            self.tick()
            ticks += 1
        return ticks

    def check_consistency(self):
        """Verify and repair rider/order consistency; return list of issues."""
        issues = []
        for rider in self.riders:
            if rider.state != 0 and rider.current_order is None:
                issues.append("Rider %d active without order" % rider.rider_id)
                rider.reset()
            for o in list(rider.orders):
                if o.status == "completed":
                    issues.append("Rider %d held completed order %d"
                                  % (rider.rider_id, o.id))
                    rider.orders.remove(o)
        return issues

    # ------------------------------------------------------------- persistence
    def to_dict(self):
        """Serialisable snapshot of the whole system."""
        return {
            "parameters": dict(self.config.params),
            "funds": self.funds,
            "tick": self.current_tick,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.orders],
        }

    def save_state(self, path=None):
        """Write the system snapshot to a JSON file."""
        path = path or self.config.get("state_file")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.to_dict(), fh, indent=2)
            return path
        except OSError as exc:
            logger.warning("Could not save state: %s", exc)
            return None


def init_system(config=None):
    """Initialise all global system parameters and return a SystemManager."""
    cfg = config or Configuration()
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", int(cfg.get("initial_funds")))
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("grid_map", GridMap())
    globalvar.set_value("config", cfg)
    return SystemManager(cfg)
