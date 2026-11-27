"""Order management and assignment."""
import globalvar
import system
from order_model import Order


def _dist(r, order):
    return abs(r.x - order.res_pos[0]) + abs(r.y - order.res_pos[1])


def find_best_rider_for_order(order):
    """Pick the nearest rider (Manhattan), preferring idle, balancing load.

    Recruits a new rider if none is idle and funds allow.
    """
    riders = globalvar.get_value("riders") or []
    if not any(r.state == 0 and not r.orders for r in riders):
        system.recruit_rider()
        riders = globalvar.get_value("riders")
    if not riders:
        return None
    return min(riders, key=lambda r: (len(r.orders), _dist(r, order),
                                      r.rider_id))


class OrderManager:
    """Creates and dispatches orders."""

    def create_order(self, coords):
        """Create order from [rx, ry, cx, cy], assign it; return
        (order, rider, new_rider_added)."""
        before = len(globalvar.get_value("riders"))
        order = Order(coords[0:2], coords[2:4])
        rider = find_best_rider_for_order(order)
        if rider is None:
            return order, None, False
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        globalvar.get_value("orders").append(order)
        return order, rider, len(globalvar.get_value("riders")) > before
