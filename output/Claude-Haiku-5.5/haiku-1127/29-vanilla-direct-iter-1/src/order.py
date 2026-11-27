"""Order assignment: distance-first rider selection and order management."""

import logging
import math
from typing import TYPE_CHECKING, List, Optional, Sequence

from globalvar import get_value, set_value
from order_model import Order

if TYPE_CHECKING:  # pragma: no cover
    from rider import Rider

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional["Rider"]:
    """Select the rider closest to the order's restaurant.

    Distance is Euclidean: ``sqrt((rider_x - restaurant_x)^2 +
    (rider_y - restaurant_y)^2)``. Ties are broken by the smaller number of
    assigned orders (load balancing), then by rider id.

    Args:
        order: The order that needs a rider.

    Returns:
        The best rider, or None if no rider exists.
    """
    best: Optional["Rider"] = None
    best_key = None
    for rider in get_value("riders") or []:
        distance = math.sqrt(
            (rider.x - order.res_pos[0]) ** 2 + (rider.y - order.res_pos[1]) ** 2
        )
        key = (distance, len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best, best_key = rider, key
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Pending orders are kept in the ``pending_orders`` global; every created
    order is also appended to the ``orders`` history global.
    """

    def __init__(self) -> None:
        """Ensure the order containers exist in global storage."""
        if get_value("pending_orders") is None:
            set_value("pending_orders", [])
        if get_value("orders") is None:
            set_value("orders", [])

    @property
    def pending(self) -> List[Order]:
        """Orders not yet assigned to a rider."""
        return get_value("pending_orders")

    @property
    def history(self) -> List[Order]:
        """All orders created during the session."""
        return get_value("orders")

    def create_order(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> Order:
        """Create an order from raw coordinates and queue it for dispatch.

        Args:
            res_pos: Restaurant ``(x, y)``.
            cus_pos: Customer ``(x, y)``.

        Returns:
            The newly created order.

        Raises:
            ValueError: If a coordinate is invalid.
        """
        order = Order(res_pos, cus_pos)
        self.pending.append(order)
        self.history.append(order)
        logger.info("Order %s created", order.id)
        return order

    def assign_pending_orders(self) -> List[Order]:
        """Assign every pending order to its best rider when possible.

        Returns:
            The list of orders that were assigned during this call.
        """
        assigned: List[Order] = []
        for order in list(self.pending):
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            rider.accept_order(order)
            self.pending.remove(order)
            assigned.append(order)
            logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return assigned

    def completed_orders(self) -> List[Order]:
        """Return all orders whose status is completed."""
        return [order for order in self.history if order.status == "completed"]

    def active_orders(self) -> List[Order]:
        """Return all orders that are not yet completed."""
        return [order for order in self.history if order.status != "completed"]
