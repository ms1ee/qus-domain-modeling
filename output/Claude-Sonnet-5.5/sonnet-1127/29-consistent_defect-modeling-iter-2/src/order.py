"""Order management and assignment."""

import math
import globalvar
from order_model import Order


def find_best_rider_for_order(order):
    """Rider with fewest pending orders, ties broken by distance."""
    riders = globalvar.get_value("riders", [])
    if not riders:
        return None
    rx, ry = order.res_pos
    return min(riders, key=lambda r: (
        r.pending_count(), math.hypot(r.x - rx, r.y - ry), r.rider_id))


class OrderManager:
    """Creates, assigns, and tracks orders."""

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

    def pending_orders(self):
        return [o for o in globalvar.get_value("orders", [])
                if o.status == "pending"]
