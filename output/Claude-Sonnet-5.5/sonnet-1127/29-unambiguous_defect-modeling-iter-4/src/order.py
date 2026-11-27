"""Order management: assignment logic."""
import globalvar
import system
from order_model import Order


def _dist(rider, order):
    return abs(rider.x - order.res_pos[0]) + abs(rider.y - order.res_pos[1])


def find_best_rider_for_order(order):
    """Pick the best rider: idle & nearest; recruit if none is idle."""
    riders = globalvar.get_value("riders") or []
    idle = [r for r in riders if r.state == 0 and not r.orders]
    if idle:
        return min(idle, key=lambda r: (_dist(r, order), r.rider_id))
    new = system.recruit_rider()
    if new is not None:
        return new
    if not riders:
        return None
    return min(riders, key=lambda r: (len(r.orders), _dist(r, order),
                                      r.rider_id))


def create_order(rx, ry, cx, cy):
    """Create an order, assign it and return (order, rider, recruited)."""
    before = len(globalvar.get_value("riders") or [])
    order = Order((rx, ry), (cx, cy))
    rider = find_best_rider_for_order(order)
    if rider is None:
        return order, None, False
    order.assign_to(rider.rider_id)
    rider.orders.append(order)
    globalvar.get_value("orders").append(order)
    recruited = len(globalvar.get_value("riders")) > before
    return order, rider, recruited
