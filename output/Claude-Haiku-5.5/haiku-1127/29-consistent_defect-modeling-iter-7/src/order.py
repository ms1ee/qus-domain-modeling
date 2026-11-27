"""Order management and rider assignment."""

import logging
import math
from typing import List, Optional, Tuple

import globalvar
from order_model import Order, STATUS_ASSIGNED, STATUS_CREATED, STATUS_PICKED_UP
from rider import Rider

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Choose the rider that should serve ``order``.

    The rider with the fewest current (undelivered) orders is preferred. Ties
    are broken by the Euclidean distance between the rider and the restaurant:
    ``sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)``.

    Args:
        order: The order that needs a rider.

    Returns:
        The selected Rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    best: Optional[Rider] = None
    best_key: Optional[Tuple[int, float]] = None
    for rider in riders:
        distance = math.sqrt(
            (rider.x - order.restaurant_x) ** 2
            + (rider.y - order.restaurant_y) ** 2
        )
        key = (rider.active_order_count(), distance)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks delivery orders.

    Attributes:
        orders: Every order created in this session (shared global list).
    """

    def __init__(self) -> None:
        """Bind to the shared order list held in global storage."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        self.orders: List[Order] = orders

    def create_order(self, restaurant_pos, customer_pos) -> Order:
        """Create an order and register it.

        Args:
            restaurant_pos: ``(x, y)`` restaurant coordinates.
            customer_pos: ``(x, y)`` customer coordinates.

        Returns:
            The newly created Order.
        """
        order = Order(restaurant_pos, customer_pos)
        self.orders.append(order)
        logger.info("Order %d created", order.id)
        return order

    def assign_order(self, order: Order) -> Optional[Rider]:
        """Assign an order to the best available rider.

        Args:
            order: Order to assign.

        Returns:
            The rider that received the order, or None if no rider exists.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return rider

    def dispatch_pending(self) -> List[Tuple[int, int]]:
        """Try to assign every queued (unassigned) order.

        Returns:
            List of ``(order_id, rider_id)`` pairs that were assigned.
        """
        assigned: List[Tuple[int, int]] = []
        for order in self.orders:
            if order.status != STATUS_CREATED:
                continue
            rider = self.assign_order(order)
            if rider is not None:
                assigned.append((order.id, rider.rider_id))
        return assigned

    def pending_orders(self) -> List[Order]:
        """Return orders that have not yet been picked up."""
        return [o for o in self.orders
                if o.status in (STATUS_CREATED, STATUS_ASSIGNED)]

    def active_orders(self) -> List[Order]:
        """Return orders that are not yet delivered."""
        return [o for o in self.orders
                if o.status in (STATUS_CREATED, STATUS_ASSIGNED, STATUS_PICKED_UP)]

    def find_order(self, order_id: int) -> Optional[Order]:
        """Return the order with ``order_id``, or None."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None
