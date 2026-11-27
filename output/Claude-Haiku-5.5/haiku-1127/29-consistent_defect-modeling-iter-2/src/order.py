"""Order management: creation, assignment and rider selection."""

import logging
import math

import globalvar
from order_model import Order, STATUS_PENDING

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Select the best rider for an order.

    Selection key (in order of priority):
        1. Fewest currently active orders.
        2. Closest by Euclidean distance to the restaurant,
           ``sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)``.
        3. Lowest rider ID (deterministic tie-break).

    Args:
        order: The :class:`Order` to be assigned.

    Returns:
        The selected :class:`Rider`, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    rest_x, rest_y = order.res_pos

    def key(rider):
        load = len(rider.active_orders())
        dist = math.hypot(rider.x - rest_x, rider.y - rest_y)
        return (load, dist, rider.rider_id)

    return min(riders, key=key)


class OrderManager:
    """Owns the list of all orders and performs assignment."""

    def __init__(self):
        """Create an empty order manager."""
        self.orders = []

    def create_order(self, restaurant_x, restaurant_y, customer_x, customer_y):
        """Create and register a new pending order.

        Args:
            restaurant_x: Restaurant x coordinate.
            restaurant_y: Restaurant y coordinate.
            customer_x: Customer x coordinate.
            customer_y: Customer y coordinate.

        Returns:
            The newly created :class:`Order`.
        """
        order = Order((restaurant_x, restaurant_y), (customer_x, customer_y))
        self.orders.append(order)
        logger.info("Order %d created", order.id)
        return order

    def assign_order(self, order):
        """Assign an order to the best available rider.

        Args:
            order: The order to assign.

        Returns:
            The rider that received the order, or None if no rider exists.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.warning("No rider available for order %d", order.id)
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return rider

    def pending_orders(self):
        """Return orders that have not yet been assigned to a rider."""
        return [o for o in self.orders if o.status == STATUS_PENDING]

    def completed_orders(self):
        """Return orders that have been delivered."""
        return [o for o in self.orders if o.status == "completed"]

    def active_orders(self):
        """Return orders that are assigned but not yet completed."""
        return [
            o for o in self.orders
            if o.status not in (STATUS_PENDING, "completed")
        ]
