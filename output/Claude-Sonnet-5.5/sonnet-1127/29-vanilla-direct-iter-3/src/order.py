"""Order assignment."""
import math
import globalvar
from rider import Rider


def find_best_rider_for_order(order):
    """Return the closest rider (Euclidean) to the restaurant, or None."""
    riders = globalvar.get_value("riders", []) or []
    best = None
    best_key = None
    for r in riders:
        d = math.hypot(r.x - order.res_pos[0], r.y - order.res_pos[1])
        key = (d, len(r.orders))
        if best_key is None or key < best_key:
            best, best_key = r, key
    return best


def recruit_if_needed(pending):
    """Recruit a rider if funds allow and pending orders exceed idle riders."""
    riders = globalvar.get_value("riders")
    funds = globalvar.get_value("funds", 0)
    idle = sum(1 for r in riders if r.state == 0 and not r.orders)
    if funds >= 300 and pending > idle:
        rid = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", rid)
        globalvar.set_value("funds", funds - 300)
        riders.append(Rider(rid))
        return True
    return False


def dispatch(order):
    """Register an order, recruit if needed, assign. Returns (rider, hired)."""
    orders = globalvar.get_value("orders")
    order.start_time = globalvar.get_value("time", 0)
    orders.append(order)
    hired = recruit_if_needed(1)
    rider = find_best_rider_for_order(order)
    if rider is not None:
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
    return rider, hired
