"""Order assignment, rider selection and order lifecycle management."""

import logging
import math
from typing import List, Optional

import globalvar
from order_model import STATUS_CREATED, Order
from rider import Rider

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the rider that should receive ``order``.

    The rider with the fewest current (uncompleted) orders is preferred.
    Ties are broken by the Euclidean distance between the rider and the
    restaurant, then by rider ID.

    Args:
        order: The order that needs a rider.

    Returns:
        The selected Rider, or None if no rider exists.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    rest_x, rest_y = order.restaurant_pos

    def ranking(rider: Rider):
        distance = math.hypot(rider.x - rest_x, rider.y - rest_y)
        return len(rider.active_orders()), distance, rider.rider_id

    return min(riders, key=ranking)


class OrderManager:
    """Creates, tracks and assigns orders.

    Attributes:
        orders (list[Order]): All orders created in this session.
    """

    def __init__(self) -> None:
        """Create an empty order manager."""
        self.orders: List[Order] = []

    def create_order(self, res_pos, cus_pos, start_time: int) -> Order:
        """Create and register a new order.

        Args:
            res_pos: Restaurant point ``(x, y)``.
            cus_pos: Customer point ``(x, y)``.
            start_time: Creation tick.

        Returns:
            The new Order.

        Raises:
            ValueError: If coordinates are invalid.
        """
        order = Order(res_pos, cus_pos, start_time)
        self.orders.append(order)
        logger.info("Order #%d created", order.id)
        return order

    def pending_orders(self) -> List[Order]:
        """Return orders that have not yet been assigned to a rider."""
        return [order for order in self.orders if order.status == STATUS_CREATED]

    def completed_orders(self) -> List[Order]:
        """Return delivered orders."""
        return [order for order in self.orders if order.completion_time is not None]

    def get_order(self, order_id: int) -> Optional[Order]:
        """Return the order with ``order_id``, or None."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    def assign(self, order: Order) -> Optional[Rider]:
        """Assign ``order`` to the best rider.

        Args:
            order: Pending order to assign.

        Returns:
            The rider that received the order, or None if no rider exists.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.warning("No rider available for order #%d", order.id)
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        rider.refresh_state()
        logger.info("Order #%d assigned to rider #%d", order.id, rider.rider_id)
        return rider
