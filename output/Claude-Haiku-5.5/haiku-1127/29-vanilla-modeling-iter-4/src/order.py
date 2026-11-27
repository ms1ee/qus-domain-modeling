"""Order management and the distance-first rider assignment algorithm."""

import logging
import math

import globalvar
from order_model import Order

logger = logging.getLogger(__name__)


class OrderManager:
    """Creates, tracks, assigns and completes orders.

    Attributes:
        orders: Every order ever created, in creation order.
        pending: Orders that do not yet have a rider.
    """

    def __init__(self):
        """Create an empty order manager."""
        self.orders = []
        self.pending = []

    def create_order(self, res_pos, cus_pos, start_time=None):
        """Create a new order and register it as pending.

        Args:
            res_pos: Restaurant position ``[x, y]``.
            cus_pos: Customer position ``[x, y]``.
            start_time: Optional creation tick.

        Returns:
            The created :class:`Order`.
        """
        order = Order(res_pos, cus_pos, start_time)
        self.orders.append(order)
        self.pending.append(order)
        logger.info("Order %d created (restaurant %s, customer %s)",
                    order.id, order.restaurant_pos, order.customer_pos)
        return order

    def assign_order(self, order, rider):
        """Assign an order to a rider by appending it to the rider's list.

        Args:
            order: The order to assign.
            rider: The :class:`Rider` receiving the order.
        """
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        if order in self.pending:
            self.pending.remove(order)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)

    def find_order(self, order_id):
        """Return the order with ``order_id`` or None if it does not exist.

        Args:
            order_id: Identifier to look up.

        Returns:
            The matching :class:`Order` or None.
        """
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    def pending_count(self):
        """Return the number of orders waiting for a rider."""
        return len(self.pending)

    def completed_orders(self):
        """Return the list of completed orders."""
        return [o for o in self.orders if o.status == Order.COMPLETED]

    def active_orders(self):
        """Return orders that are not yet completed."""
        return [o for o in self.orders if o.status != Order.COMPLETED]


def find_best_rider_for_order(order):
    """Pick the rider closest to the order's restaurant.

    Distance is Euclidean: ``sqrt((rider_x - restaurant_x)^2 +
    (rider_y - restaurant_y)^2)``. Ties are broken by the smaller number of
    assigned orders (load balancing), then by the lower rider ID.

    Args:
        order: The :class:`Order` to be assigned.

    Returns:
        The best :class:`Rider`, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None

    def ranking(rider):
        distance = math.sqrt((rider.x - order.restaurant_x) ** 2
                             + (rider.y - order.restaurant_y) ** 2)
        return (distance, len(rider.orders), rider.rider_id)

    return min(riders, key=ranking)
