"""System initialization and management."""
import globalvar


def init_system():
    """Initialize core parameters."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])


def create_rider():
    """Create a rider, deducting cost."""
    from rider import Rider
    cid = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", cid)
    globalvar.set_value("funds", globalvar.get_value("funds", 0) - 300)
    r = Rider(cid)
    globalvar.get_value("riders").append(r)
    return r


def tick():
    """Advance all riders one tick."""
    globalvar.set_value("time", globalvar.get_value("time", 0) + 1)
    for r in globalvar.get_value("riders", []):
        r.move()
