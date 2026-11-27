"""System initialization and core operations."""
import globalvar

RIDER_COST = 300
ORDER_INCOME = 100


def init_system():
    """Initialize all global parameters."""
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", 0)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("grid_size", 8)
    globalvar.set_value("cell_size", 100)


def recruit_rider(force=False):
    """Create a rider if funds >= cost (or forced). Returns the rider or None."""
    from rider import Rider
    funds = globalvar.get_value("funds", 0)
    if funds < RIDER_COST and not force:
        return None
    globalvar.set_value("funds", funds - RIDER_COST)
    rid = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", rid)
    rider = Rider(rid)
    globalvar.get_value("riders").append(rider)
    return rider


def tick():
    """Advance simulation by one tick."""
    globalvar.set_value("tick", globalvar.get_value("tick", 0) + 1)
    for r in globalvar.get_value("riders", []):
        r.move()
