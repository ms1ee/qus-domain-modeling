"""Order assignment logic.

Implements the closest-rider-first assignment strategy based on Euclidean
distance, with a per-rider capacity limit that balances load among riders.
"""

import logging
import math

from globalvar import get_value
from order_model import Order, STATUS_PENDING
from rider import Rider

logger = logging.getLogger(__name__)

MAX_ORDERS_PER_RIDER = 3


def _euclidean(rider: Rider, point: tuple) -> float:
    """Return the Euclidean distance between a rider and a point."""
    return math.sqrt((rider.x - point[0]) ** 2 + (rider.y - point[1]) ** 2)


def find_best_rider_for_order(order: Order) -> Rider:
    """Choose the best rider for an order.

    The closest rider (Euclidean distance to the restaurant) is preferred.
    Riders already holding ``MAX_ORDERS_PER_RIDER`` orders are excluded. Ties
    are broken by fewer assigned orders and then by lower rider ID.

    Args:
        order: The order to assign.

    Returns:
        The selected Rider, or None if no rider has spare capacity.
    """
    riders = get_value("riders") or []
    candidates = [r for r in riders if len(r.orders) < MAX_ORDERS_PER_RIDER]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda r: (
            _euclidean(r, order.res_pos),
            len(r.orders),
            r.rider_id,
        ),
    )


class OrderManager:
    """Creates, assigns and tracks orders."""

    @staticmethod
    def create_order(res_pos, cus_pos) -> Order:
        """Create an order and register it in the global order history.

        Args:
            res_pos: Restaurant (x, y) in range 0-800.
            cus_pos: Customer (x, y) in range 0-800.

        Returns:
            The created Order.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        order = Order(res_pos, cus_pos)
        get_value("orders").append(order)
        return order

    @staticmethod
    def pending_orders() -> list:
        """Return all orders that have not yet been assigned to a rider."""
        return [o for o in get_value("orders") or [] if o.status == STATUS_PENDING]

    @staticmethod
    def assign(order: Order):
        """Assign an order to the best available rider.

        Args:
            order: The order to assign.

        Returns:
            The rider that received the order, or None if none is available.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.info("No rider available for order %d", order.id)
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return rider
