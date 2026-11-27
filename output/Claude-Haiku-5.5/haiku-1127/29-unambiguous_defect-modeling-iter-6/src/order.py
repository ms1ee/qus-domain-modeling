"""Order assignment: rider selection and order management.

Riders are scored with a distance-first measure. Each order already held by
a rider adds a load penalty, which spreads work across riders.
"""

import logging
from typing import List, Optional

import globalvar
from order_model import FINISHED_STATUSES, STATUS_REJECTED, Order
from rider import Rider

logger = logging.getLogger(__name__)

MAX_ORDERS_PER_RIDER = 3
LOAD_PENALTY = 150


def _manhattan(a: tuple, b: tuple) -> int:
    """Return the Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the best rider for an order.

    Score = Manhattan distance from the rider to the restaurant
            + LOAD_PENALTY * number of orders already held.
    Riders at MAX_ORDERS_PER_RIDER are not eligible. Ties go to the earlier
    rider in the list.

    Args:
        order: The order to assign.

    Returns:
        The selected Rider, or None if no rider has spare capacity.
    """
    riders = globalvar.get_value("riders", []) or []
    best: Optional[Rider] = None
    best_score = None
    for rider in riders:
        if rider.load >= MAX_ORDERS_PER_RIDER:
            continue
        distance = _manhattan(rider.position, order.restaurant_pos)
        score = distance + LOAD_PENALTY * rider.load
        if best is None or score < best_score:
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        orders: All orders created in this session.
    """

    def __init__(self) -> None:
        self.orders: List[Order] = []

    def create_order(self, restaurant_x: int, restaurant_y: int,
                     customer_x: int, customer_y: int) -> Order:
        """Create and register an order.

        Raises:
            ValueError: If any coordinate is invalid.
        """
        order = Order((restaurant_x, restaurant_y), (customer_x, customer_y))
        self.orders.append(order)
        return order

    def assign_order(self, order: Order) -> Optional[Rider]:
        """Assign an order to the best available rider.

        Returns:
            The rider that received the order, or None if none had capacity.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order #%s assigned to rider #%s", order.id, rider.rider_id)
        return rider

    def get_order(self, order_id: int) -> Optional[Order]:
        """Return the order with ``order_id`` or None."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    def active_orders(self) -> List[Order]:
        """Return orders that are not completed, failed or rejected."""
        return [o for o in self.orders if o.status not in FINISHED_STATUSES]

    def completed_orders(self) -> List[Order]:
        """Return orders that have been delivered."""
        return [o for o in self.orders if o.status == "completed"]

    def reject(self, order: Order) -> None:
        """Mark an order as rejected because it could not be assigned."""
        order.set_status(STATUS_REJECTED)
