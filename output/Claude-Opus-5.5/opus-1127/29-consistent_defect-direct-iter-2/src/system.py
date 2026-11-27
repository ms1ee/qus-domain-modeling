"""System initialisation and rider recruitment."""

import globalvar

INITIAL_FUNDS = 1000
RECRUIT_COST = 500
RECRUIT_THRESHOLD = 300


def init_system(funds=INITIAL_FUNDS):
    """Initialise all core system parameters."""
    globalvar._init()
    globalvar.set_value("money", funds)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("orders", [])
    globalvar.set_value("time", 0)


def _ensure_init():
    if globalvar.get_value("riders") is None:
        globalvar.set_value("riders", [])
    if globalvar.get_value("money") is None:
        globalvar.set_value("money", INITIAL_FUNDS)
    if globalvar.get_value("rider_id_counter") is None:
        globalvar.set_value("rider_id_counter", 0)
    if globalvar.get_value("orders") is None:
        globalvar.set_value("orders", [])
    if globalvar.get_value("time") is None:
        globalvar.set_value("time", 0)


def recruit_rider(force=False):
    """Recruit a new rider if funds allow (>= 300). Returns the rider or None."""
    from rider import Rider
    _ensure_init()
    money = globalvar.get_value("money")
    if not force and money < RECRUIT_THRESHOLD:
        return None
    counter = globalvar.get_value("rider_id_counter") + 1
    globalvar.set_value("rider_id_counter", counter)
    globalvar.set_value("money", money - RECRUIT_COST)
    rider = Rider(counter)
    globalvar.get_value("riders").append(rider)
    return rider


def pending_order_count():
    """Number of orders not yet accepted/started by any rider."""
    _ensure_init()
    count = 0
    for o in globalvar.get_value("orders"):
        if o.status in ("pending", "assigned"):
            count += 1
    return count


def idle_rider_count():
    """Number of idle riders with no outstanding work."""
    _ensure_init()
    return sum(1 for r in globalvar.get_value("riders")
               if r.state == 0 and not r.active_orders())


def auto_recruit():
    """Recruit a rider if funds >= 300 and pending orders exceed idle riders."""
    _ensure_init()
    if (globalvar.get_value("money") >= RECRUIT_THRESHOLD
            and pending_order_count() > idle_rider_count()):
        return recruit_rider()
    return None
