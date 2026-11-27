"""Order assignment logic (OrderManager)."""

import math

import globalvar


def _distance(rider, order):
    rx, ry = order.res_pos
    return math.sqrt((rider.x - rx) ** 2 + (rider.y - ry) ** 2)


def find_best_rider_for_order(order):
    """Return the rider closest (Euclidean) to the order's restaurant.

    Idle riders are preferred; if none are idle, the closest rider overall is
    chosen (ties broken by queue length, then rider id).  Returns None when
    there are no riders.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    idle = [r for r in riders if r.state == 0 and not r.orders]
    pool = idle if idle else riders
    return min(pool, key=lambda r: (_distance(r, order), len(r.orders),
                                    r.rider_id))


class OrderManager:
    """Handles creation, assignment and completion queries of orders."""

    def __init__(self):
        if globalvar.get_value("orders") is None:
            globalvar.set_value("orders", [])

    @property
    def orders(self):
        """All orders."""
        return globalvar.get_value("orders", [])

    def create_order(self, rx, ry, cx, cy):
        """Create and register a new order."""
        from order_model import Order
        order = Order((rx, ry), (cx, cy))
        self.orders.append(order)
        return order

    def assign(self, order):
        """Assign ``order`` to the best rider; return the rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        if order not in rider.orders:
            rider.orders.append(order)
        order.assign_to(rider.rider_id)
        return rider

    def pending_orders(self):
        """Orders not yet assigned to a rider."""
        return [o for o in self.orders if o.status == "pending"]

    def completed_orders(self):
        """Orders that have been delivered."""
        return [o for o in self.orders if o.status == "completed"]
