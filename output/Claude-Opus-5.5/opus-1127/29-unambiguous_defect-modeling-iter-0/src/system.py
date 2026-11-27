"""System initialisation and resource management."""

import logging

import globalvar
from rider import Rider, RiderState

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruitment_cost": 100,
    "max_riders": 20,
    "rider_speed": 20,
    "ticks_per_command": 1,
}


def init_system(config=None):
    """Initialise all global runtime state.

    Args:
        config: optional dict overriding :data:`DEFAULT_CONFIG` values.

    Returns:
        The effective configuration dict.
    """
    cfg = dict(DEFAULT_CONFIG)
    if config:
        for key, value in config.items():
            if key in DEFAULT_CONFIG:
                try:
                    cfg[key] = int(value)
                except (TypeError, ValueError):
                    logger.warning("Ignoring invalid config value %s=%r", key, value)
    globalvar._init()
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("recruitment_cost", int(cfg["recruitment_cost"]))
    globalvar.set_value("max_riders", int(cfg["max_riders"]))
    globalvar.set_value("rider_speed", int(cfg["rider_speed"]))
    globalvar.set_value("ticks_per_command", max(0, int(cfg["ticks_per_command"])))
    return cfg


def get_riders():
    """Return the global rider list (creating it if needed)."""
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    return riders


def can_recruit():
    """True if funds and the rider limit allow a new rider."""
    funds = globalvar.get_value("funds", 0) or 0
    cost = globalvar.get_value("recruitment_cost", DEFAULT_CONFIG["recruitment_cost"])
    max_riders = globalvar.get_value("max_riders", DEFAULT_CONFIG["max_riders"])
    return funds >= cost and len(get_riders()) < max_riders


def recruit_rider(force=False):
    """Recruit a new rider, deducting the recruitment cost.

    Returns:
        The new Rider, or None if recruitment is not possible.
    """
    if not force and not can_recruit():
        return None
    riders = get_riders()
    counter = globalvar.get_value("rider_id_counter", 0) or 0
    existing = [r.rider_id for r in riders]
    if existing:
        counter = max(counter, max(existing))
    counter += 1
    rider = Rider(counter)
    riders.append(rider)
    cost = globalvar.get_value("recruitment_cost", DEFAULT_CONFIG["recruitment_cost"])
    globalvar.set_value("funds", (globalvar.get_value("funds", 0) or 0) - cost)
    globalvar.set_value("rider_id_counter", counter)
    logger.info("Recruited rider %d", counter)
    return rider


def advance_tick(n=1):
    """Advance the simulation ``n`` ticks, moving every rider."""
    for _ in range(max(0, int(n))):
        globalvar.set_value("tick", (globalvar.get_value("tick", 0) or 0) + 1)
        for rider in list(get_riders()):
            try:
                rider.move()
            except Exception:  # keep the simulation alive
                logger.exception("Rider %s failed to move", rider.rider_id)


def all_idle():
    """True when no rider has outstanding orders."""
    return all(not r.orders for r in get_riders())


def check_consistency():
    """Check and repair global state. Returns a list of repair messages."""
    fixes = []
    funds = globalvar.get_value("funds", 0)
    if not isinstance(funds, int):
        try:
            globalvar.set_value("funds", int(funds))
        except (TypeError, ValueError):
            globalvar.set_value("funds", 0)
        fixes.append("funds reset to integer")
    if not isinstance(globalvar.get_value("tick", 0), int):
        globalvar.set_value("tick", 0)
        fixes.append("tick reset")
    seen = set()
    riders = get_riders()
    for rider in list(riders):
        if rider.rider_id in seen:
            riders.remove(rider)
            fixes.append("removed duplicate rider %s" % rider.rider_id)
            continue
        seen.add(rider.rider_id)
        if rider.state not in (RiderState.IDLE, RiderState.PICKING_UP,
                               RiderState.DELIVERING):
            rider.state = RiderState.IDLE
            fixes.append("rider %s state reset" % rider.rider_id)
        before = len(rider.orders)
        rider.orders = [o for o in rider.orders if o.status != "completed"]
        if len(rider.orders) != before:
            fixes.append("rider %s completed orders removed" % rider.rider_id)
        if not rider.orders and rider.state != RiderState.IDLE:
            rider.state = RiderState.IDLE
            fixes.append("rider %s set idle" % rider.rider_id)
    if seen:
        counter = globalvar.get_value("rider_id_counter", 0) or 0
        if counter < max(seen):
            globalvar.set_value("rider_id_counter", max(seen))
            fixes.append("rider id counter fixed")
    return fixes


class SystemManager:
    """Object facade over the global system state."""

    def __init__(self, config=None):
        self.config = init_system(config)

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

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
        return globalvar.get_value("tick", 0)

    @property
    def recruitment_cost(self):
        return globalvar.get_value("recruitment_cost", 0)

    def recruit_rider(self, force=False):
        """See :func:`recruit_rider`."""
        return recruit_rider(force)

    def tick(self, n=1):
        """See :func:`advance_tick`."""
        advance_tick(n)

    def run_until_idle(self, max_ticks=10000):
        """Advance until every order is delivered. Returns ticks used."""
        used = 0
        while not all_idle() and used < max_ticks:
            advance_tick(1)
            used += 1
        return used

    def check_consistency(self):
        """See :func:`check_consistency`."""
        return check_consistency()
