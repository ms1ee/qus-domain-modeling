"""System initialization and management."""
import globalvar

RECRUIT_COST = 300
DELIVERY_FEE = 100


def init_system():
    """Initialize all global state."""
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", 0)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("grid_size", 8)
    globalvar.set_value("cell_size", 100)


def add_rider():
    """Create a new rider with an auto-incremented id."""
    from rider import Rider
    rid = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", rid)
    r = Rider(rid)
    globalvar.get_value("riders").append(r)
    return r


def check_recruit():
    """Recruit a rider if funds >= 300. Returns the new rider or None."""
    funds = globalvar.get_value("funds", 0)
    if funds >= RECRUIT_COST:
        globalvar.set_value("funds", funds - RECRUIT_COST)
        return add_rider()
    return None


def tick():
    """Advance the simulation one tick."""
    globalvar.set_value("time", globalvar.get_value("time", 0) + 1)
    for r in list(globalvar.get_value("riders")):
        r.move()
