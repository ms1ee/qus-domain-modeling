"""Order management."""
import math

import globalvar
from order_model import Order


def find_best_rider_for_order(order):
    """Rider with fewest current orders, ties by distance to restaurant."""
    riders = globalvar.get_value("riders", [])
    best = None
    best_key = None
    for r in riders:
        d = math.hypot(r.x - order.res_pos[0], r.y - order.res_pos[1])
        key = (r.pending_count(), d)
        if best_key is None or key < best_key:
            best, best_key = r, key
    return best


class OrderManager:
    """Creates, assigns and tracks orders."""

    def create_order(self, rx, ry, cx, cy):
        order = Order((rx, ry), (cx, cy))
        globalvar.get_value("orders").append(order)
        return order

    def assign(self, order):
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider

    def unassigned(self):
        return [o for o in globalvar.get_value("orders")
                if o.status == "pending"]
