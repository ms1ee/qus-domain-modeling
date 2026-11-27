"""Order management: creation, assignment and rider selection."""

import logging
import math
from typing import List, Optional, Sequence

import globalvar
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the rider that should receive ``order``.

    The rider with the fewest active orders is preferred. Ties are broken by
    the Euclidean distance from the rider to the restaurant:
    sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2).

    Args:
        order: Order that needs a rider.

    Returns:
        The selected Rider, or None when no rider exists.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    rest_x, rest_y = order.res_pos

    def sort_key(rider: Rider):
        """Sort riders by load first, then by distance to the restaurant."""
        distance = math.sqrt((rider.x - rest_x) ** 2 + (rider.y - rest_y) ** 2)
        return (len(rider.active_orders()), distance, rider.rider_id)

    return min(riders, key=sort_key)


class OrderManager:
    """Creates, assigns and reports on orders."""

    @staticmethod
    def _orders() -> List[Order]:
        """Return the global order list, creating it if necessary."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords: Sequence[int]) -> Order:
        """Create an order from ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Args:
            coords: Four integer coordinates (already validated).

        Returns:
            The newly created Order, stored in the global order list.

        Raises:
            ValueError: If ``coords`` does not contain exactly four values.
        """
        if len(coords) != 4:
            raise ValueError("an order needs exactly four coordinates")
        tick = int(globalvar.get_value("tick", 0) or 0)
        order = Order(coords[0:2], coords[2:4], created_tick=tick)
        self._orders().append(order)
        logger.info("order %s created res=%s cus=%s", order.id, order.res_pos, order.cus_pos)
        return order

    def pending_orders(self) -> List[Order]:
        """Return orders that have not been assigned to a rider yet."""
        return [order for order in self._orders() if order.status == "pending"]

    def completed_orders(self) -> List[Order]:
        """Return orders that have been delivered."""
        return [order for order in self._orders() if order.status == "completed"]

    def assign_order(self, order: Order) -> Optional[Rider]:
        """Assign ``order`` to the best available rider.

        Args:
            order: A pending order.

        Returns:
            The rider that received the order, or None if no rider exists.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("order %s assigned to rider %s", order.id, rider.rider_id)
        return rider
