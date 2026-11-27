"""Order management."""
import globalvar
from order_model import Order


def find_best_rider_for_order(order):
    """Pick rider with fewest active orders, then nearest to restaurant."""
    riders = globalvar.get_value("riders", [])
    if not riders:
        return None

    def key(r):
        d = ((r.x - order.res_pos[0]) ** 2
             + (r.y - order.res_pos[1]) ** 2) ** 0.5
        return (len(r.pending_orders()), d, r.rider_id)

    return min(riders, key=key)


class OrderManager:
    """Create and assign orders."""

    @staticmethod
    def create(coords):
        o = Order(coords[0:2], coords[2:4])
        orders = globalvar.get_value("orders")
        orders.append(o)
        return o

    @staticmethod
    def assign(order):
        r = find_best_rider_for_order(order)
        if r is None:
            return None
        order.assign_to(r.rider_id)
        r.orders.append(order)
        return r
