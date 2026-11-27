"""Order management and intelligent rider assignment."""

import logging
import math

import globalvar
from order_model import Order

logger = logging.getLogger(__name__)

MAX_ORDERS_PER_RIDER = 3


def find_best_rider_for_order(order):
    """Find the closest rider able to take ``order``.

    Distance is the Euclidean distance from the rider to the restaurant:
    ``sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)``.
    Ties are broken by the lighter current load, then by rider id. Riders
    already holding ``MAX_ORDERS_PER_RIDER`` orders are skipped to balance
    load.

    Args:
        order: The order needing a rider.

    Returns:
        The best ``Rider`` object, or None when no rider is available.
    """
    riders = globalvar.get_value("riders", []) or []
    rest_x, rest_y = order.restaurant
    best = None
    best_key = None
    for rider in riders:
        if len(rider.orders) >= MAX_ORDERS_PER_RIDER:
            continue
        distance = math.hypot(rider.x - rest_x, rider.y - rest_y)
        key = (distance, len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        orders: List of all orders ever created (pending, assigned, completed).
    """

    def __init__(self):
        """Create an empty order manager."""
        self.orders = []

    def create_order(self, res_pos, cus_pos, start_time=0):
        """Create and register a new pending order.

        Args:
            res_pos: Restaurant ``(x, y)`` in range 0-800.
            cus_pos: Customer ``(x, y)`` in range 0-800.
            start_time: Current simulation tick.

        Returns:
            The new ``Order``.

        Raises:
            OrderValidationError: If coordinates are invalid.
        """
        order = Order(res_pos, cus_pos, start_time)
        self.orders.append(order)
        logger.info("Created order %d", order.id)
        return order

    def pending_orders(self):
        """Return orders that have not yet been assigned to a rider."""
        return [o for o in self.orders if o.status == Order.PENDING]

    def assign(self, order, rider):
        """Assign ``order`` to ``rider`` by appending it to the rider's orders.

        Args:
            order: The order to assign.
            rider: The receiving rider.
        """
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Assigned order %d to rider %d", order.id, rider.rider_id)

    def to_list(self):
        """Return all orders as JSON-serialisable dictionaries."""
        return [o.to_dict() for o in self.orders]
