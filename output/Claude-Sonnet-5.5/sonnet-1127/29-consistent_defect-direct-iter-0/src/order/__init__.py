"""Order management and assignment."""
import globalvar
from order_model import Order


def _pending(r):
    return sum(1 for o in r.orders if o.status != "completed")


def find_best_rider_for_order(order):
    """Pick rider with fewest pending orders, ties by distance."""
    riders = globalvar.get_value("riders")
    if not riders:
        return None
    rx, ry = order.res_pos
    return min(riders, key=lambda r: (
        _pending(r), ((r.x - rx) ** 2 + (r.y - ry) ** 2) ** 0.5))


class OrderManager:
    """Create and assign orders."""

    def create_order(self, res, cus):
        """Create an order, recruit if needed, and assign it."""
        from system import SystemManager
        order = Order(res, cus)
        new = SystemManager().recruit_if_needed(
            force=not globalvar.get_value("riders"))
        rider = find_best_rider_for_order(order)
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        return order, rider, new is not None
