"""Order assignment."""
import globalvar
from rider import Rider


def recruit_rider():
    """Create a new rider if funds allow."""
    funds = globalvar.get_value("funds", 0)
    if funds < 300:
        return None
    cid = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", cid)
    globalvar.set_value("funds", funds - 300)
    r = Rider(cid)
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    riders.append(r)
    return r


def find_best_rider_for_order(order):
    """Return the rider closest to the order's restaurant."""
    riders = globalvar.get_value("riders") or []
    if not riders:
        return recruit_rider()
    rx, ry = order.res_pos
    return min(riders, key=lambda r: (r.x - rx) ** 2 + (r.y - ry) ** 2)


def assign_order(order):
    """Find the best rider and give the order to them."""
    rider = find_best_rider_for_order(order)
    if rider is not None:
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
    return rider
