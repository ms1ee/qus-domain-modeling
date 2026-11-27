"""Order assignment logic and the order manager.

Assignment strategy: closest eligible rider first, with a load penalty per
already-assigned order so work is spread among riders (competitive
assignment for load balancing).
"""

import logging
from typing import List, Optional

import config
import globalvar
from grid import manhattan
from order_model import STATUS_PENDING, Order
from rider import Rider

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Find the best rider for an order.

    Score = distance from the rider to the restaurant
            + load_penalty * number of orders already held.
    Riders already holding ``max_orders_per_rider`` orders are skipped.
    Ties are broken by the lower rider ID.

    Args:
        order: The order needing a rider.

    Returns:
        The best Rider, or None if no rider is eligible.
    """
    max_orders = int(config.CONFIG["max_orders_per_rider"])
    penalty = int(config.CONFIG["load_penalty"])
    best: Optional[Rider] = None
    best_score: Optional[int] = None
    for rider in globalvar.get_value("riders", []) or []:
        if len(rider.orders) >= max_orders:
            continue
        distance = manhattan(rider.position, order.restaurant_center)
        score = distance + penalty * len(rider.orders)
        if (
            best is None
            or score < best_score
            or (score == best_score and rider.rider_id < best.rider_id)
        ):
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates orders, assigns them to riders and tracks pending orders.

    Attributes:
        pending: Orders waiting for an eligible rider.
    """

    def __init__(self) -> None:
        """Create an empty order manager."""
        self.pending: List[Order] = []

    def create_order(self, res_pos, cus_pos) -> Order:
        """Create an order and register it in the global order history.

        Args:
            res_pos: Restaurant ``(x, y)`` input coordinate.
            cus_pos: Customer ``(x, y)`` input coordinate.

        Returns:
            The newly created Order.

        Raises:
            ValueError: If a coordinate is invalid.
        """
        order = Order(res_pos, cus_pos)
        globalvar.get_value("orders").append(order)
        logger.info("Created order %d", order.id)
        return order

    def try_assign(self, order: Order) -> Optional[Rider]:
        """Attempt to assign an order to the best available rider.

        If no rider is eligible, the order is kept in the pending queue.

        Args:
            order: The order to assign.

        Returns:
            The rider that received the order, or None.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            if order not in self.pending and order.status == STATUS_PENDING:
                self.pending.append(order)
            logger.info("Order %d queued (no rider available)", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        if order in self.pending:
            self.pending.remove(order)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return rider

    def assign_pending(self) -> List[Order]:
        """Try to assign every pending order.

        Returns:
            The list of orders that were assigned during this call.
        """
        assigned: List[Order] = []
        for order in list(self.pending):
            if self.try_assign(order) is not None:
                assigned.append(order)
        return assigned
