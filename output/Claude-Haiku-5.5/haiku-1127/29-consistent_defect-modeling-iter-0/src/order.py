"""Order assignment and order management.

Assignment strategy:
    1. Only riders with the fewest active orders are considered.
    2. Among those, the rider closest to the restaurant wins, using the
       Euclidean distance formula from the PRD.
"""

import logging
import math
from typing import Any, List, Optional, Sequence

import globalvar
from config import ORDER_PENDING
from order_model import Order

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional[Any]:
    """Select the rider that should receive ``order``.

    Args:
        order: The order needing a rider.

    Returns:
        The chosen :class:`rider.Rider`, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    min_load = min(len(r.active_orders) for r in riders)
    candidates = [r for r in riders if len(r.active_orders) == min_load]
    rx, ry = order.res_pos
    return min(
        candidates,
        key=lambda r: (math.hypot(r.x - rx, r.y - ry), r.rider_id),
    )


class OrderManager:
    """Create, assign and query orders stored in the global order list."""

    @property
    def orders(self) -> List[Order]:
        """The list of all orders known to the system."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, res_pos: Sequence[int],
                     cus_pos: Sequence[int]) -> Order:
        """Create and store a new pending order.

        Raises:
            ValueError: If either location is invalid.
        """
        order = Order(res_pos, cus_pos)
        self.orders.append(order)
        logger.info("Created order %s", order.id)
        return order

    def create_order_from_list(self, values: Sequence[int]) -> Order:
        """Create an order from ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the list is malformed.
        """
        if len(values) != 4:
            raise ValueError("Exactly four coordinates are required.")
        return self.create_order((values[0], values[1]), (values[2], values[3]))

    def pending_orders(self) -> List[Order]:
        """Return orders that have not been assigned to a rider yet."""
        return [o for o in self.orders if o.status == ORDER_PENDING]

    def assign_order(self, order: Order) -> Optional[Any]:
        """Assign ``order`` to the best rider and append it to that rider.

        Returns:
            The rider that received the order, or None if none is available.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.warning("No rider available for order %s", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Assigned order %s to rider %s", order.id, rider.rider_id)
        return rider
