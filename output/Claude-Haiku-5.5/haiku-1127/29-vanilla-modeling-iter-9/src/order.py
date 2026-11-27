"""Order management and rider assignment.

Assignment uses the closest-rider-first strategy based on Euclidean distance
from each rider to the restaurant.  Ties are broken by the smaller current
workload, which balances load among riders.
"""

import logging
import math

import globalvar
from order_model import Order, STATUS_COMPLETED, STATUS_PENDING

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Return the rider closest to the order's restaurant.

    The distance is ``sqrt((rider_x - restaurant_x)**2 + (rider_y - restaurant_y)**2)``.
    Ties are broken by fewer assigned orders, then by lower rider ID.

    Args:
        order (Order): the order to be assigned.

    Returns:
        Rider | None: the best rider, or None when no rider exists.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    rest_x, rest_y = order.res_pos
    best = None
    best_key = None
    for rider in riders:
        distance = math.sqrt((rider.x - rest_x) ** 2 + (rider.y - rest_y) ** 2)
        key = (round(distance, 6), len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        orders (list[Order]): every order created in this session.
    """

    def __init__(self):
        """Create an empty order manager."""
        self.orders = []

    def create_order(self, res_pos, cus_pos):
        """Create and register a new order.

        Args:
            res_pos (list | tuple): restaurant ``[x, y]``.
            cus_pos (list | tuple): customer ``[x, y]``.

        Returns:
            Order: the newly created pending order.
        """
        order = Order(res_pos, cus_pos)
        self.orders.append(order)
        logger.info("Order %d created", order.id)
        return order

    def pending_orders(self):
        """Return orders that have not yet been assigned to a rider."""
        return [order for order in self.orders if order.status == STATUS_PENDING]

    def completed_orders(self):
        """Return orders that have been delivered."""
        return [order for order in self.orders if order.status == STATUS_COMPLETED]

    def find_order(self, order_id):
        """Return the order with ``order_id`` or None."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    def assign(self, order):
        """Assign ``order`` to the best rider by appending it to ``rider.orders``.

        Args:
            order (Order): a pending order.

        Returns:
            Rider | None: the rider that received the order, or None if no
            rider is available.

        Raises:
            ValueError: if the order is not pending.
        """
        if order.status != STATUS_PENDING:
            raise ValueError(f"Order {order.id} is not pending")
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return rider
