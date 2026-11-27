"""Order management: creation, assignment and history."""

import logging

import globalvar
from order_model import Order
from path_planner import manhattan

logger = logging.getLogger("dispatch.order")


def find_best_rider_for_order(order, riders=None):
    """Return the best rider for ``order`` (closest rider first).

    For an idle rider the cost is its Manhattan distance to the restaurant.
    For a busy rider the cost is its remaining queued work plus the distance
    from its final drop-off to the restaurant, which balances load among
    competing riders.  Ties are broken by fewer pending orders, then lower id.
    Returns ``None`` if there are no riders.
    """
    if riders is None:
        riders = globalvar.get_value("riders") or []
    best, best_key = None, None
    for rider in riders:
        work, end = rider.estimate_workload()
        cost = work + manhattan(end, order.res_pos)
        key = (cost, len(rider.pending_orders()), rider.rider_id)
        if best_key is None or key < best_key:
            best, best_key = rider, key
    return best


class OrderManager:
    """Handles order creation, assignment and completion records."""

    def __init__(self, assignment_strategy="nearest"):
        self.assignment_strategy = assignment_strategy
        if globalvar.get_value("orders") is None:
            globalvar.set_value("orders", [])

    def _orders(self):
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords):
        """Create and register an order from ``[rx, ry, cx, cy]``."""
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        orders = self._orders()
        orders.append(order)
        limit = globalvar.get_value("max_order_history", 10000)
        if limit and len(orders) > limit:
            for o in list(orders):
                if len(orders) <= limit:
                    break
                if o.status == "completed":
                    orders.remove(o)
        logger.info("Created order %d", order.id)
        return order

    def assign_to_rider(self, order, rider):
        """Assign ``order`` to ``rider``."""
        order.assign_to(rider.rider_id)
        rider.orders.append(order)

    def assign_order(self, order):
        """Assign ``order`` to the best rider; returns the rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is not None:
            self.assign_to_rider(order, rider)
        return rider

    def get_orders(self):
        return list(self._orders())

    def get_order(self, order_id):
        for o in self._orders():
            if o.id == order_id:
                return o
        return None

    def completed_orders(self):
        return [o for o in self._orders() if o.status == "completed"]
