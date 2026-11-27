"""Order management and rider assignment.

Assignment strategy: the rider closest (Euclidean distance) to the restaurant
receives the order. Ties are broken by the smaller current workload so that
load is spread across riders.
"""

import logging
import math

from globalvar import get_value
from order_model import Order

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Find the best rider for an order.

    The distance is ``sqrt((rider_x - restaurant_x)^2 + (rider_y -
    restaurant_y)^2)``. Among riders, the one with the smallest distance wins;
    ties are resolved by fewer assigned orders, then by rider id.

    Args:
        order: The Order that needs a rider.

    Returns:
        The selected Rider, or None when no riders exist.
    """
    riders = get_value("riders") or []
    best = None
    best_key = None
    for rider in riders:
        distance = math.hypot(rider.x - order.restaurant_x,
                              rider.y - order.restaurant_y)
        key = (round(distance, 6), len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        orders: Every order ever created, in creation order.
        pending: Orders waiting for a rider.
    """

    def __init__(self):
        """Create an empty order manager."""
        self.orders = []
        self.pending = []

    def create_order(self, restaurant_pos, customer_pos):
        """Create an order from raw coordinates and queue it as pending.

        Args:
            restaurant_pos: (x, y) restaurant coordinates.
            customer_pos: (x, y) customer coordinates.

        Returns:
            The newly created Order.
        """
        order = Order(restaurant_pos, customer_pos)
        self.orders.append(order)
        self.pending.append(order)
        return order

    def pending_count(self):
        """Return the number of orders waiting for a rider."""
        return len(self.pending)

    def assign_pending(self):
        """Assign pending orders to the best available riders.

        Returns:
            List of orders assigned during this call.
        """
        assigned = []
        for order in list(self.pending):
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            rider.orders.append(order)
            order.assign_to(rider.rider_id)
            self.pending.remove(order)
            assigned.append(order)
            logger.info("Order %d assigned to rider %d", order.id,
                        rider.rider_id)
        return assigned

    def find_order(self, order_id):
        """Return the order with ``order_id`` or None."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    def completed_orders(self):
        """Return all completed orders."""
        return [order for order in self.orders if order.status == "completed"]
