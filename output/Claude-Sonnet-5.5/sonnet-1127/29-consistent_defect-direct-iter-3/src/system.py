"""System initialization and main loop."""
import globalvar
from rider import Rider
from order import assign_order
from order_model import Order


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])


def maybe_recruit():
    """Recruit a rider if funds >= 300 and pending > idle riders."""
    riders = globalvar.get_value("riders")
    orders = globalvar.get_value("orders")
    pending = sum(1 for o in orders if o.rider_id is None)
    idle = sum(1 for r in riders if r.pending_count() == 0)
    if globalvar.get_value("funds") >= 300 and pending > idle:
        rid = globalvar.get_value("rider_id_counter") + 1
        globalvar.set_value("rider_id_counter", rid)
        globalvar.set_value("funds", globalvar.get_value("funds") - 500)
        riders.append(Rider(rid))
        return True
    return False


def submit_order(coords):
    """Create an order, recruit if needed, assign. Returns (order, rider, recruited)."""
    order = Order(coords[:2], coords[2:])
    globalvar.get_value("orders").append(order)
    recruited = maybe_recruit()
    rider = assign_order(order)
    return order, rider, recruited


def tick():
    """Advance simulation one tick."""
    globalvar.set_value("time", globalvar.get_value("time") + 1)
    for r in globalvar.get_value("riders"):
        r.move()
