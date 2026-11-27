"""Order assignment."""
import math

import globalvar
from rider import Rider
from order_model import Order

RECRUIT_COST = 500
RECRUIT_MIN_FUNDS = 300


def find_best_rider_for_order(order):
    """Rider with fewest orders, ties broken by distance to restaurant."""
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None

    def key(r):
        d = math.hypot(r.x - order.res_pos[0], r.y - order.res_pos[1])
        return (r.pending_count(), d, r.rider_id)

    return min(riders, key=key)


def maybe_recruit():
    """Recruit a rider if conditions hold. Returns the new rider or None."""
    riders = globalvar.get_value("riders")
    funds = globalvar.get_value("funds")
    orders = globalvar.get_value("orders", [])
    pending = sum(1 for o in orders if o.status != "completed")
    idle = sum(1 for r in riders if r.pending_count() == 0)
    if not riders or (funds >= RECRUIT_MIN_FUNDS and pending > idle):
        if funds < RECRUIT_MIN_FUNDS and riders:
            return None
        rid = globalvar.get_value("rider_id_counter") + 1
        globalvar.set_value("rider_id_counter", rid)
        globalvar.set_value("funds", funds - RECRUIT_COST)
        r = Rider(rid)
        riders.append(r)
        return r
    return None


def assign_order(order):
    """Register, possibly recruit, and assign the order.

    Returns (rider, new_rider_or_None).
    """
    globalvar.get_value("orders").append(order)
    new = maybe_recruit()
    rider = find_best_rider_for_order(order)
    if rider is None:
        return None, new
    order.assign_to(rider.rider_id)
    rider.orders.append(order)
    return rider, new


def create_order(rx, ry, cx, cy):
    return Order((rx, ry), (cx, cy))
