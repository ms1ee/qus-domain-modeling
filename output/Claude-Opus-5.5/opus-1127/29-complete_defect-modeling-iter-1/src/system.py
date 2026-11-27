"""System manager: funds, riders, simulated time and orchestration."""

import logging

import globalvar
from config import Configuration
from display import DisplayManager
from grid_map import GridMap, clamp_coord
from input_manager import InputManager
from order import OrderManager, find_best_rider_for_order
from path_planner import PathPlanner
from rider import Rider, RiderState

logger = logging.getLogger("dispatch.system")


class SystemManager:
    """Core manager; state is stored in :mod:`globalvar`."""

    def __init__(self, configuration=None):
        self.config = configuration or Configuration()
        self.order_manager = OrderManager()
        self.path_planner = PathPlanner()
        self.grid_map = GridMap()
        self.display_manager = DisplayManager()
        self.input_manager = InputManager()

    # ---------------------------------------------------------------- properties
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
        return self.order_manager.get_orders()

    @property
    def running(self):
        return globalvar.get_value("running", False)

    @property
    def current_time(self):
        return globalvar.get_value("time", 0)

    @property
    def rider_id_counter(self):
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def recruitment_threshold(self):
        return globalvar.get_value("recruitment_threshold", 300)

    # ------------------------------------------------------------------ riders
    def recruit_rider(self):
        """Create a new rider, paying the rider cost."""
        new_id = self.rider_id_counter + 1
        globalvar.set_value("rider_id_counter", new_id)
        rider = Rider(new_id)
        self.riders.append(rider)
        self.funds = self.funds - int(self.config.get("rider_cost"))
        logger.info("Recruited rider %d", new_id)
        return rider

    def auto_recruit(self):
        """Recruit a rider if funds reach the threshold; returns it or None."""
        if self.funds >= self.recruitment_threshold and \
                len(self.riders) < int(self.config.get("max_riders")):
            return self.recruit_rider()
        return None

    def get_rider(self, rider_id):
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    # ------------------------------------------------------------------ orders
    def submit_order(self, coords):
        """Create and assign an order from four coordinates.

        Returns a dict with keys ``order``, ``rider``, ``recruited``,
        ``route``, ``eta`` and ``busy``.
        """
        coords = InputManager.validate_coordinates(coords)
        recruited = self.auto_recruit()
        if not self.riders:
            recruited = self.recruit_rider()
        order = self.order_manager.create_order(coords)
        rider = find_best_rider_for_order(order, self.riders)
        _, start = rider.estimate_workload()
        busy = bool(rider.pending_orders()) or rider.state != RiderState.IDLE
        route = self.path_planner.plan_multi([start, order.res_pos, order.cus_pos])
        self.order_manager.assign_to_rider(order, rider)
        return {
            "order": order,
            "rider": rider,
            "recruited": recruited,
            "route": route,
            "eta": route.estimated_time(rider.speed),
            "busy": busy,
        }

    # -------------------------------------------------------------- simulation
    def tick(self, n=1):
        """Advance simulated time by ``n`` ticks."""
        for _ in range(max(0, int(n))):
            globalvar.set_value("time", self.current_time + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # pragma: no cover - defensive recovery
                    logger.exception("Rider %s failed to move; recovering", rider.rider_id)
                    rider.reset()

    def check_consistency(self):
        """Repair inconsistent state; returns a list of fix descriptions."""
        fixes = []
        for rider in self.riders:
            if int(rider.state) not in (0, 1, 2):
                rider.reset()
                fixes.append("Rider %s had invalid state; reset" % rider.rider_id)
            elif rider.state != RiderState.IDLE and (
                    rider.current_order is None
                    or rider.current_order.status == "completed"):
                rider.reset()
                fixes.append("Rider %s busy without order; reset" % rider.rider_id)
            if rider.x != clamp_coord(rider.x) or rider.y != clamp_coord(rider.y):
                rider.x, rider.y = clamp_coord(rider.x), clamp_coord(rider.y)
                fixes.append("Rider %s position clamped" % rider.rider_id)
        ids = {r.rider_id for r in self.riders}
        for order in self.order_manager.get_orders():
            if order.status == "completed":
                continue
            if order.rider_id not in ids:
                if not self.riders:
                    self.recruit_rider()
                rider = find_best_rider_for_order(order, self.riders)
                self.order_manager.assign_to_rider(order, rider)
                fixes.append("Order %d reassigned to rider %s" % (order.id, rider.rider_id))
        return fixes

    def stop(self):
        globalvar.set_value("running", False)

    def snapshot(self):
        """Return a JSON-serializable snapshot of the system."""
        return {
            "parameters": self.config.parameters,
            "system": {
                "funds": self.funds,
                "time": self.current_time,
                "rider_id_counter": self.rider_id_counter,
            },
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.get_orders()],
        }

    def save_data(self, path=None):
        """Persist the snapshot to a JSON file."""
        path = path or self.config.get("data_file")
        return Configuration.save_data(path, self.snapshot())


def init_system(config_path=None):
    """Initialise global state and return a :class:`SystemManager`."""
    config = Configuration(config_path)
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("orders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("funds", int(config.get("initial_funds")))
    globalvar.set_value("recruitment_threshold", int(config.get("recruitment_threshold")))
    globalvar.set_value("rider_speed", int(config.get("rider_speed")))
    start = config.get("rider_start")
    globalvar.set_value("rider_start", (int(start[0]), int(start[1])))
    globalvar.set_value("base_fee", int(config.get("base_fee")))
    globalvar.set_value("fee_per_100_units", int(config.get("fee_per_100_units")))
    globalvar.set_value("max_order_history", int(config.get("max_order_history")))
    globalvar.set_value("max_log_entries", int(config.get("max_log_entries")))
    globalvar.set_value("grid_map", GridMap())
    manager = SystemManager(config)
    globalvar.set_value("system_manager", manager)
    return manager
