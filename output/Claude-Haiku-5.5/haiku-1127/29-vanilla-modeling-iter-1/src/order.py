"""Order assignment: nearest-rider selection and pending order management."""

import logging
import math
from typing import List, Optional

import globalvar
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the closest rider to the order's restaurant.

    Distance is Euclidean: sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2).
    Ties are broken by the current workload (fewer orders wins), then by ID,
    which balances load among equally placed riders.

    Args:
        order: The order to assign.

    Returns:
        The best Rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders", [])
    rx, ry = order.res_center
    best: Optional[Rider] = None
    best_key = None
    for rider in riders:
        distance = math.hypot(rider.x - rx, rider.y - ry)
        key = (round(distance, 6), len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates orders, keeps the order history and assigns pending orders."""

    @property
    def orders(self) -> List[Order]:
        """Full order history."""
        return globalvar.get_value("orders", [])

    @property
    def pending(self) -> List[Order]:
        """Orders that have not yet been assigned to a rider."""
        return globalvar.get_value("pending_orders", [])

    def create_order(self, res_pos, cus_pos) -> Order:
        """Create an order and queue it for assignment.

        Args:
            res_pos: [restaurant_x, restaurant_y].
            cus_pos: [customer_x, customer_y].

        Returns:
            The created Order.

        Raises:
            ValueError: If coordinates are invalid.
        """
        order = Order(res_pos, cus_pos)
        self.orders.append(order)
        self.pending.append(order)
        logger.info("Order %d queued", order.id)
        return order

    def assign_pending(self) -> List[Order]:
        """Assign every pending order that can be matched to a rider.

        Returns:
            List of orders that were assigned in this call.
        """
        assigned: List[Order] = []
        remaining: List[Order] = []
        for order in self.pending:
            rider = find_best_rider_for_order(order)
            if rider is None:
                remaining.append(order)
                continue
            rider.orders.append(order)
            order.assign_to(rider.rider_id)
            assigned.append(order)
            logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        self.pending[:] = remaining
        return assigned

    def find_order(self, order_id: int) -> Optional[Order]:
        """Return the order with the given ID, or None."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None
