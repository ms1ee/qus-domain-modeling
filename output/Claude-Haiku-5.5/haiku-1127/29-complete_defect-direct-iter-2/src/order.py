"""Order management: rider selection, submission and assignment.

``find_best_rider_for_order`` implements the distance-first assignment
strategy with a load penalty. ``OrderManager`` creates orders, assigns them
and queues orders that cannot yet be served.
"""

import logging

import globalvar
from config import SETTINGS
from order_model import STATUS_COMPLETED, Order
from path_planner import manhattan

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Choose the best rider for an order.

    Closest rider first: the score is the Manhattan distance from the rider
    to the restaurant plus a penalty per order already held by that rider,
    which balances load across riders. Riders already at the maximum number
    of orders are excluded unless every rider is at capacity.

    Args:
        order: The Order needing a rider.

    Returns:
        The selected Rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    max_orders = SETTINGS["max_orders_per_rider"]
    penalty = SETTINGS["load_penalty"]
    candidates = [r for r in riders if len(r.orders) < max_orders] or riders

    def score(rider):
        """Return the sort key for a candidate rider."""
        distance = manhattan(rider.position, order.res_pos)
        return (distance + penalty * len(rider.orders), rider.rider_id)

    return min(candidates, key=score)


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        active_orders: Orders that are not yet completed.
    """

    def __init__(self):
        """Create an empty order manager."""
        self.active_orders = []

    @staticmethod
    def all_orders():
        """Return the history list of every order created.

        Returns:
            List of Order objects.
        """
        return globalvar.get_value("orders")

    @staticmethod
    def pending_orders():
        """Return orders waiting for a rider.

        Returns:
            List of pending Order objects.
        """
        return globalvar.get_value("pending_orders")

    def submit(self, res_pos, cus_pos):
        """Create an order and try to assign it immediately.

        If no rider can take it, the order is queued as pending.

        Args:
            res_pos: ``[restaurant_x, restaurant_y]``.
            cus_pos: ``[customer_x, customer_y]``.

        Returns:
            The created Order.
        """
        order = Order(res_pos, cus_pos)
        globalvar.get_value("orders").append(order)
        self.active_orders.append(order)
        if not self.assign(order):
            globalvar.get_value("pending_orders").append(order)
            logger.info("Order #%d queued: no rider available", order.id)
        return order

    def assign(self, order):
        """Assign an order to the best available rider.

        The order is appended to the rider's ``orders`` list.

        Args:
            order: The Order to assign.

        Returns:
            True if the order was assigned, False otherwise.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return False
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order #%d assigned to rider #%d", order.id,
                    rider.rider_id)
        return True

    def assign_pending(self):
        """Retry assignment for every queued order.

        Returns:
            List of orders assigned during this call.
        """
        pending = globalvar.get_value("pending_orders")
        still_waiting = []
        assigned = []
        for order in pending:
            if self.assign(order):
                assigned.append(order)
            else:
                still_waiting.append(order)
        pending[:] = still_waiting
        return assigned

    def collect_completed(self):
        """Remove completed orders from the active list.

        Returns:
            List of orders that were completed and removed.
        """
        done = [o for o in self.active_orders if o.status == STATUS_COMPLETED]
        self.active_orders = [o for o in self.active_orders
                              if o.status != STATUS_COMPLETED]
        return done
