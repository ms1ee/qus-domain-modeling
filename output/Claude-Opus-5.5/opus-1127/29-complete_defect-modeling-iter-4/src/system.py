"""System initialisation and core management (funds, riders, ticks)."""

import logging

import globalvar
from config import Configuration
from order import OrderManager
from order_model import ORDER_COMPLETED
from path_planner import clamp
from rider import Rider, RiderState

logger = logging.getLogger(__name__)


class SystemManager:
    """Core class managing funds, riders and simulated time.

    All state is stored in :mod:`globalvar`; this class offers operations.
    """

    def __init__(self, configuration=None):
        self.configuration = configuration or Configuration()
        self.order_manager = OrderManager()

    # -------------------------------------------------------------- props
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
    def running(self):
        return bool(globalvar.get_value("running", False))

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0)

    @property
    def recruitment_threshold(self):
        return globalvar.get_value("recruitment_threshold", 300)

    # ------------------------------------------------------------ riders
    def recruit_rider(self):
        """Create a new rider with an auto-incremented ID."""
        rider_id = globalvar.get_value("rider_id_counter", 0) or 0
        rider = Rider(rider_id)
        globalvar.set_value("rider_id_counter", rider_id + 1)
        self.riders.append(rider)
        return rider

    def remove_rider(self, rider_id):
        """Remove an idle rider. Returns True on success."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                if rider.has_pending_orders():
                    return False
                self.riders.remove(rider)
                return True
        return False

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def check_recruitment(self):
        """Recruit riders while funds >= threshold. Returns new riders."""
        new_riders = []
        cost = globalvar.get_value("rider_cost", 300) or 0
        threshold = self.recruitment_threshold
        guard = 0
        while self.funds >= threshold and guard < 100:
            guard += 1
            new_riders.append(self.recruit_rider())
            self.funds = self.funds - cost
            if cost <= 0:
                break
        return new_riders

    # ------------------------------------------------------------ orders
    def place_order(self, coords):
        """Handle the ``start`` command.

        :return: dict with keys order, rider, route, new_riders.
        """
        new_riders = self.check_recruitment()
        order = self.order_manager.create_order(coords)
        rider, route = self.order_manager.assign_order(order)
        return {"order": order, "rider": rider, "route": route,
                "new_riders": new_riders}

    # -------------------------------------------------------------- time
    def advance_tick(self, count=1):
        """Advance the simulation ``count`` ticks."""
        for _ in range(max(0, int(count))):
            globalvar.set_value("tick", (self.current_tick or 0) + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception as exc:  # recovery
                    logger.exception("Rider %s failed to move: %s",
                                     rider.rider_id, exc)
                    self.check_consistency()
            self.check_recruitment()
            self.order_manager.dispatch_pending()

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    # -------------------------------------------------------- consistency
    def check_consistency(self):
        """Repair inconsistent rider states. Returns number of fixes."""
        fixes = 0
        for rider in self.riders:
            before = len(rider.orders)
            rider.orders[:] = [o for o in rider.orders
                               if o.status != ORDER_COMPLETED]
            fixes += before - len(rider.orders)
            rider.x, rider.y = clamp(rider.x), clamp(rider.y)
            if rider.state not in (RiderState.IDLE, RiderState.PICKING_UP,
                                   RiderState.DELIVERING):
                rider.state = RiderState.IDLE
                fixes += 1
            if rider.state != RiderState.IDLE and (
                    rider.current_order is None
                    or rider.current_order not in rider.orders):
                rider.state = RiderState.IDLE
                rider.current_order = None
                rider.path = []
                fixes += 1
        if not isinstance(self.funds, int):
            self.funds = int(self.funds or 0)
            fixes += 1
        return fixes

    def save(self, path=None):
        """Persist the state as JSON."""
        return self.configuration.save_state(path)


def init_system(config_path=None):
    """Initialise all global system parameters.

    Rider list empty, rider ID counter 0, running True, tick 0.
    :return: SystemManager
    """
    globalvar._init()
    configuration = Configuration(config_path)
    params = configuration.load()
    for key, value in params.items():
        globalvar.set_value(key, value)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("funds", int(params.get("initial_funds", 300)))
    globalvar.set_value("orders", [])
    globalvar.set_value("pending_orders", [])
    globalvar.set_value("order_id_counter", 0)
    return SystemManager(configuration)
