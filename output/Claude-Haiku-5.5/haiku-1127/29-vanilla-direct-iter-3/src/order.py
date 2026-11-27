"""Order assignment: nearest-rider selection and order management."""

import logging
import math
from typing import TYPE_CHECKING, List, Optional, Sequence

import globalvar
from order_model import Order

if TYPE_CHECKING:
    from rider import Rider

logger = logging.getLogger(__name__)

MAX_ORDERS_PER_RIDER = 3


def find_best_rider_for_order(order: Order) -> Optional["Rider"]:
    """Select the rider closest to the order's restaurant.

    Distance is Euclidean: sqrt((rider_x - restaurant_x)^2 +
    (rider_y - restaurant_y)^2). Riders already holding
    MAX_ORDERS_PER_RIDER orders are skipped unless every rider is full,
    which provides load balancing. Ties go to the rider with fewer orders.

    Args:
        order: The order to assign.

    Returns:
        The chosen Rider, or None if no rider exists.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    rest_x, rest_y = order.res_pos
    candidates = [r for r in riders if len(r.orders) < MAX_ORDERS_PER_RIDER]
    if not candidates:
        candidates = list(riders)
    return min(
        candidates,
        key=lambda r: (math.hypot(r.x - rest_x, r.y - rest_y),
                       len(r.orders), r.rider_id),
    )


class OrderManager:
    """Creates orders, assigns them to riders and tracks order history."""

    def create_order(self, res_pos: Sequence[int],
                     cus_pos: Sequence[int]) -> Order:
        """Create an order and register it in the global order list.

        Args:
            res_pos: Restaurant coordinates ``(x, y)``.
            cus_pos: Customer coordinates ``(x, y)``.

        Returns:
            The newly created Order.

        Raises:
            TypeError, ValueError: If coordinates are invalid.
        """
        order = Order(res_pos, cus_pos)
        orders = globalvar.get_value("orders")
        if orders is not None:
            orders.append(order)
        logger.info("Order %s created: restaurant %s, customer %s",
                    order.id, order.res_pos, order.cus_pos)
        return order

    def assign_order(self, order: Order) -> Optional["Rider"]:
        """Assign an order to the best rider by appending it to rider.orders.

        Args:
            order: Order to assign.

        Returns:
            The rider that received the order, or None if no rider exists.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.info("Order %s could not be assigned: no riders",
                        order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order %s assigned to rider %s",
                    order.id, rider.rider_id)
        return rider

    @staticmethod
    def completed_orders() -> List[Order]:
        """Return the list of delivered orders."""
        return list(globalvar.get_value("completed_orders") or [])
