"""System initialisation and resource management."""

import logging

import globalvar
from rider import Rider

logger = logging.getLogger(__name__)

DEFAULT_FUNDS = 1000
RECRUIT_COST = 500
RECRUIT_THRESHOLD = 300


def init_system():
    """Initialise all global system parameters."""
    globalvar._init()
    globalvar.set_value("funds", DEFAULT_FUNDS)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("current_time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("recruit_cost", RECRUIT_COST)
    globalvar.set_value("recruit_threshold", RECRUIT_THRESHOLD)
    logger.info("System initialised")


def _riders():
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    return riders


def _orders():
    orders = globalvar.get_value("orders")
    if orders is None:
        orders = []
        globalvar.set_value("orders", orders)
    return orders


def recruit_rider():
    """Recruit a new rider if funds allow. Returns the rider or None."""
    funds = globalvar.get_value("funds", DEFAULT_FUNDS)
    threshold = globalvar.get_value("recruit_threshold", RECRUIT_THRESHOLD)
    cost = globalvar.get_value("recruit_cost", RECRUIT_COST)
    if funds is None or funds < threshold:
        return None
    riders = _riders()
    counter = globalvar.get_value("rider_id_counter", 0) or 0
    existing = [r.rider_id for r in riders if isinstance(r.rider_id, int)]
    if existing:
        counter = max(counter, max(existing))
    counter += 1
    rider = Rider(counter)
    riders.append(rider)
    globalvar.set_value("rider_id_counter", counter)
    globalvar.set_value("funds", funds - cost)
    logger.info("Recruited rider %s (funds now %s)", counter, funds - cost)
    return rider


def pending_order_count():
    """Number of orders not yet assigned to a rider."""
    return sum(1 for o in _orders() if o.status == "pending")


def idle_rider_count():
    """Number of idle riders."""
    return sum(1 for r in _riders() if r.is_idle())


def auto_recruit():
    """Recruit a rider when funds >= threshold and pending orders exceed
    idle riders. Returns the new rider or None."""
    funds = globalvar.get_value("funds", DEFAULT_FUNDS)
    threshold = globalvar.get_value("recruit_threshold", RECRUIT_THRESHOLD)
    if funds is not None and funds >= threshold and \
            pending_order_count() > idle_rider_count():
        return recruit_rider()
    return None


def tick(count=1):
    """Advance the simulation by ``count`` ticks."""
    for _ in range(max(0, int(count))):
        globalvar.set_value("current_time",
                            (globalvar.get_value("current_time", 0) or 0) + 1)
        for rider in list(_riders()):
            try:
                rider.move()
            except Exception:  # pragma: no cover - recovery path
                logger.exception("Rider %s failed to move; resetting",
                                 getattr(rider, "rider_id", "?"))
                rider.path = []
                rider.current_order = None


def check_consistency():
    """Run state consistency checks; returns a list of problem strings."""
    problems = []
    ids = [r.rider_id for r in _riders()]
    if len(ids) != len(set(ids)):
        problems.append("Duplicate rider ids")
    for rider in _riders():
        if not (0 <= rider.x <= 800 and 0 <= rider.y <= 800):
            problems.append("Rider {} out of map".format(rider.rider_id))
        if rider.state not in (0, 1, 2):
            problems.append("Rider {} invalid state".format(rider.rider_id))
    return problems


class SystemManager:
    """Object oriented facade over the global system state."""

    def __init__(self, initialise=False):
        if initialise or globalvar.get_value("riders") is None:
            init_system()

    @property
    def funds(self):
        return globalvar.get_value("funds", DEFAULT_FUNDS)

    @property
    def riders(self):
        return _riders()

    @property
    def orders(self):
        return _orders()

    @property
    def current_time(self):
        return globalvar.get_value("current_time", 0) or 0

    @property
    def running(self):
        return bool(globalvar.get_value("running", True))

    def stop(self):
        globalvar.set_value("running", False)

    def recruit(self):
        return recruit_rider()

    def auto_recruit(self):
        return auto_recruit()

    def tick(self, count=1):
        tick(count)

    def get_rider(self, rider_id):
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def remove_rider(self, rider_id):
        rider = self.get_rider(rider_id)
        if rider is not None and not rider.active_orders():
            self.riders.remove(rider)
            return True
        return False
