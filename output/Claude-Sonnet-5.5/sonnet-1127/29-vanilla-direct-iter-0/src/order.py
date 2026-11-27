"""Order management."""

import math

import globalvar
from order_model import Order


def find_best_rider_for_order(order):
    """Return the closest rider (idle riders preferred), or None."""
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    idle = [r for r in riders if r.state == 0 and not r.orders]
    pool = idle or riders

    def key(r):
        d = math.hypot(r.x - order.res_pos[0], r.y - order.res_pos[1])
        return (d, len(r.orders), r.rider_id)

    return min(pool, key=key)


def create_order(coords):
    """Create an order from [rx, ry, cx, cy]."""
    return Order((coords[0], coords[1]), (coords[2], coords[3]))


def assign_order(order):
    """Assign order to the best rider; return the rider or None."""
    rider = find_best_rider_for_order(order)
    if rider is None:
        return None
    order.assign_to(rider.rider_id)
    rider.orders.append(order)
    orders = globalvar.get_value("orders")
    if orders is not None and order not in orders:
        orders.append(order)
    return rider
