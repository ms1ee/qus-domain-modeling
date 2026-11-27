"""Order management and rider assignment."""

import logging
import math
from typing import List, Optional, Sequence

import globalvar
from order_model import ORDER_COMPLETED, ORDER_PENDING, Order

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order):
    """Select the best rider for an order.

    The primary criterion is the Euclidean distance between the rider's
    current position and the restaurant. Ties are broken by the rider with
    the fewest active orders, then by rider ID.

    Args:
        order: The order to be assigned.

    Returns:
        The chosen Rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    best = None
    best_key = None
    for rider in riders:
        distance = math.sqrt(
            (rider.x - order.restaurant_x) ** 2 + (rider.y - order.restaurant_y) ** 2
        )
        key = (distance, rider.active_order_count(), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    All orders are stored in the global ``"orders"`` list.
    """

    def _all(self) -> List[Order]:
        """Return the global order list, creating it when absent."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, restaurant_pos: Sequence[int], customer_pos: Sequence[int]) -> Order:
        """Create a new pending order from raw input coordinates.

        Args:
            restaurant_pos: Restaurant ``(x, y)`` in 0-800.
            customer_pos: Customer ``(x, y)`` in 0-800.

        Returns:
            The newly created Order.

        Raises:
            ValueError: If a coordinate is invalid.
        """
        order = Order(restaurant_pos, customer_pos)
        self._all().append(order)
        logger.info("created order %d", order.id)
        return order

    def all_orders(self) -> List[Order]:
        """Return every order ever created, in creation order."""
        return list(self._all())

    def pending_orders(self) -> List[Order]:
        """Return orders that have not yet been assigned to a rider."""
        return [o for o in self._all() if o.status == ORDER_PENDING]

    def get_order(self, order_id: int) -> Optional[Order]:
        """Return the order with ``order_id`` or None."""
        for order in self._all():
            if order.id == order_id:
                return order
        return None

    def assign_pending_orders(self) -> List[Order]:
        """Assign every pending order to its best available rider.

        Returns:
            The list of orders assigned during this call.
        """
        assigned: List[Order] = []
        for order in self.pending_orders():
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            rider.orders.append(order)
            order.assign_to(rider.rider_id)
            assigned.append(order)
            logger.info("assigned order %d to rider %d", order.id, rider.rider_id)
        return assigned

    def completed_orders(self) -> List[Order]:
        """Return orders that have been delivered."""
        return [o for o in self._all() if o.status == ORDER_COMPLETED]
