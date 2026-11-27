"""Order assignment and order lifecycle management."""

import logging
import math
from typing import List, Optional

from globalvar import get_value
from order_model import Order, STATUS_COMPLETED, STATUS_PENDING
from rider import Rider

logger = logging.getLogger("dispatch.order")


def active_order_count(rider: Rider) -> int:
    """Return the number of unfinished orders for a rider.

    Args:
        rider: Rider to inspect.
    """
    return sum(1 for o in rider.orders if o.status != STATUS_COMPLETED)


def find_best_rider_for_order(order: Order) -> Rider:
    """Choose the rider that should receive an order.

    Riders with the fewest current orders are preferred; ties are broken
    by Euclidean distance to the restaurant, then by rider id.

    Args:
        order: Order that needs a rider.

    Returns:
        The selected Rider, or None if no rider exists.
    """
    riders = get_value("riders") or []
    if not riders:
        return None

    def sort_key(rider: Rider):
        distance = math.hypot(rider.x - order.restaurant_x, rider.y - order.restaurant_y)
        return (active_order_count(rider), distance, rider.rider_id)

    return min(riders, key=sort_key)


class OrderManager:
    """Creates, assigns and tracks orders."""

    def __init__(self) -> None:
        """Create an empty order manager."""
        self.orders: List[Order] = []

    def create_order(self, res_pos, cus_pos) -> Order:
        """Create and register a new pending order.

        Args:
            res_pos: Restaurant (x, y).
            cus_pos: Customer (x, y).

        Returns:
            The newly created Order.
        """
        order = Order(res_pos, cus_pos)
        self.orders.append(order)
        logger.info("Order %d created", order.id)
        return order

    def pending_orders(self) -> List[Order]:
        """Return orders that have not yet been assigned to a rider."""
        return [o for o in self.orders if o.status == STATUS_PENDING]

    def completed_orders(self) -> List[Order]:
        """Return delivered orders."""
        return [o for o in self.orders if o.status == STATUS_COMPLETED]

    def assign_order(self, order: Order) -> Optional[Rider]:
        """Assign an order to the best available rider.

        Args:
            order: Pending order to assign.

        Returns:
            The rider that accepted the order, or None if no rider exists.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.warning("No rider available for order %d", order.id)
            return None
        rider.accept_order(order)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return rider
