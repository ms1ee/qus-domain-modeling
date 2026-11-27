"""System initialisation and resource management."""

import logging

import globalvar
from config import DEFAULT_CONFIG
from grid_map import GridMap
from rider import Rider, RiderState

logger = logging.getLogger(__name__)


def init_system(config=None):
    """Initialise all global system parameters."""
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    globalvar._init()
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("current_tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("recruitment_cost", int(cfg["recruitment_cost"]))
    globalvar.set_value("rider_speed", int(cfg["rider_speed"]))
    globalvar.set_value("rider_start", tuple(int(v) for v in cfg["rider_start"]))
    globalvar.set_value("grid_map", GridMap())
    globalvar.set_value("config", cfg)
    logger.info("System initialised: %s", cfg)


def get_riders():
    """Return the rider list (creating it if absent)."""
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    return riders


def get_orders():
    """Return the global order list."""
    orders = globalvar.get_value("orders")
    if orders is None:
        orders = []
        globalvar.set_value("orders", orders)
    return orders


def recruit_rider():
    """Create a new rider, deducting the recruitment cost from funds."""
    counter = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    rider = Rider(counter)
    get_riders().append(rider)
    cost = globalvar.get_value("recruitment_cost", 300)
    globalvar.set_value("funds", globalvar.get_value("funds", 0) - cost)
    logger.info("Recruited rider %s", counter)
    return rider


def pending_order_count():
    """Number of orders not yet being worked on."""
    return sum(1 for o in get_orders() if o.status in ("pending", "assigned"))


def idle_rider_count():
    """Number of idle riders with empty queues."""
    return sum(1 for r in get_riders() if r.is_idle())


def check_recruitment():
    """Recruit riders while funds allow and pending orders exceed idle riders.

    Returns the list of newly recruited riders.
    """
    recruited = []
    cost = globalvar.get_value("recruitment_cost", 300)
    while (globalvar.get_value("funds", 0) >= cost
           and pending_order_count() > idle_rider_count()):
        recruited.append(recruit_rider())
    return recruited


def validate_state():
    """Check and repair system state consistency. Returns list of issues."""
    issues = []
    for rider in get_riders():
        if rider.state not in (0, 1, 2):
            issues.append("Rider %s had invalid state %r" % (rider.rider_id, rider.state))
            rider.state = RiderState.IDLE
            rider.path = []
        if rider.state != RiderState.IDLE and not rider.orders:
            issues.append("Rider %s busy without orders" % rider.rider_id)
            rider.state = RiderState.IDLE
            rider.path = []
        rider.orders = [o for o in rider.orders if o.status != "completed"]
    for issue in issues:
        logger.warning(issue)
    return issues


def advance_tick(n=1):
    """Advance the simulation by ``n`` ticks."""
    from order import dispatch_pending_orders  # avoid circular import
    for _ in range(max(0, int(n))):
        tick = globalvar.get_value("current_tick", 0) + 1
        globalvar.set_value("current_tick", tick)
        for rider in list(get_riders()):
            try:
                rider.move()
            except Exception as exc:  # recover from unexpected failure
                logger.exception("Error moving rider %s: %s", rider.rider_id, exc)
                validate_state()
        dispatch_pending_orders()


class SystemManager:
    """Object facade over the global system state."""

    def __init__(self, config=None, initialise=True):
        if initialise:
            init_system(config)
        self.grid_map = globalvar.get_value("grid_map") or GridMap()

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def riders(self):
        return get_riders()

    @property
    def rider_id_counter(self):
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def current_tick(self):
        return globalvar.get_value("current_tick", 0)

    @property
    def recruitment_cost(self):
        return globalvar.get_value("recruitment_cost", 300)

    def recruit_rider(self):
        return recruit_rider()

    def check_recruitment(self):
        return check_recruitment()

    def tick(self, n=1):
        advance_tick(n)

    def validate(self):
        return validate_state()

    def stop(self):
        self.running = False
