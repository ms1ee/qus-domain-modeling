"""System initialization and management."""
import globalvar
from rider import Rider

RIDER_COST = 300


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", 0)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])


def recruit_rider():
    """Create a new rider if funds allow; return it or None."""
    funds = globalvar.get_value("funds", 0)
    if funds < RIDER_COST:
        return None
    globalvar.set_value("funds", funds - RIDER_COST)
    rid = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", rid)
    rider = Rider(rid)
    globalvar.get_value("riders").append(rider)
    return rider


def tick():
    """Advance simulation one tick."""
    globalvar.set_value("tick", globalvar.get_value("tick", 0) + 1)
    for r in globalvar.get_value("riders"):
        r.move()
