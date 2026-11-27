"""Order management and rider assignment.

Assignment strategy: the closest rider is preferred. Each order already queued
on a rider adds a load penalty, which spreads work across riders (load
balancing) instead of overloading one rider.
"""

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

from globalvar import get_value
from order_model import Order

if TYPE_CHECKING:  # pragma: no cover - only for type checkers
    from rider import Rider

logger = logging.getLogger(__name__)

LOAD_PENALTY = 150  # distance-equivalent cost of each order already queued


def find_best_rider_for_order(order: Order) -> "Rider":
    """Find the best rider for an order.

    The score of a rider is the Manhattan distance from its position to the
    restaurant plus ``LOAD_PENALTY`` per queued order. Ties are broken by the
    lower rider ID.

    Args:
        order: Order that needs a rider.

    Returns:
        The selected Rider, or None if no riders exist.
    """
    riders = get_value("riders", []) or []
    rest_x, rest_y = order.restaurant_pos
    best = None
    best_key: Optional[Tuple[int, int]] = None
    for rider in riders:
        distance = abs(rider.x - rest_x) + abs(rider.y - rest_y)
        key = (distance + LOAD_PENALTY * len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates orders, assigns them to riders and tracks their status."""

    def __init__(self) -> None:
        """Create an empty order manager."""
        self.orders: List[Order] = []
        self.pending: List[Order] = []

    def create_order(self, restaurant_pos, customer_pos) -> Order:
        """Create and register a new order.

        Args:
            restaurant_pos: ``[x, y]`` restaurant location.
            customer_pos: ``[x, y]`` customer location.

        Returns:
            The created Order.
        """
        order = Order(restaurant_pos, customer_pos)
        self.orders.append(order)
        return order

    def assign(self, order: Order) -> Optional["Rider"]:
        """Assign an order to the best rider without queueing it.

        The order is appended to ``rider.orders`` and recorded on the order.

        Args:
            order: Order to assign.

        Returns:
            The rider that received the order, or None if no rider exists.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return rider

    def submit(self, order: Order) -> Optional["Rider"]:
        """Assign an order, or queue it as pending when no rider is available."""
        rider = self.assign(order)
        if rider is None:
            order.status = "queued"
            self.pending.append(order)
            logger.warning("No rider available; order %d queued", order.id)
        return rider

    def retry_pending(self) -> List[Order]:
        """Try to assign every pending order.

        Returns:
            Orders that were assigned during this call.
        """
        assigned: List[Order] = []
        for order in list(self.pending):
            if self.assign(order) is not None:
                self.pending.remove(order)
                assigned.append(order)
        return assigned

    def active_orders(self) -> List[Order]:
        """Return orders that have not been completed yet."""
        return [o for o in self.orders if o.status != "completed"]

    def completed_orders(self) -> List[Order]:
        """Return completed orders."""
        return [o for o in self.orders if o.status == "completed"]
