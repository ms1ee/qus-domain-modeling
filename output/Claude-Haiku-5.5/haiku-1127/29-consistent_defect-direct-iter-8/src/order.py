"""Order creation, assignment and the nearest-rider selection algorithm."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple

import globalvar
from order_model import COMPLETED, Order

if TYPE_CHECKING:  # pragma: no cover - typing only
    from rider import Rider

logger = logging.getLogger(__name__)


def euclidean_distance(a: Sequence[int], b: Sequence[int]) -> float:
    """Return ``sqrt((ax - bx)^2 + (ay - by)^2)``."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def find_best_rider_for_order(order: Order) -> Optional["Rider"]:
    """Select the rider that should receive ``order``.

    Selection key, in priority order:
        1. Fewest current (non-completed) orders, so load is always balanced.
        2. Closest to the restaurant by distance
           ``sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)``.
        3. Lowest rider ID as a deterministic tie-breaker.

    Args:
        order: The order that needs a rider.

    Returns:
        The chosen rider, or None when no rider exists.
    """
    riders = globalvar.get_value("riders") or []
    best: Optional["Rider"] = None
    best_key: Optional[Tuple[int, float, int]] = None
    for rider in riders:
        key = (
            len(rider.active_orders()),
            euclidean_distance(rider.position, order.res_pos),
            rider.rider_id,
        )
        if best_key is None or key < best_key:
            best, best_key = rider, key
    if best is not None:
        logger.debug("Order %s matched to rider %s", order.id, best.rider_id)
    return best


class OrderManager:
    """Creates, assigns and tracks orders."""

    @property
    def orders(self) -> List[Order]:
        """Full order history stored in the global store."""
        return globalvar.get_value("orders")

    def create_order(self, values: Sequence[int]) -> Order:
        """Create an order from ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Args:
            values: Four integers already validated to be in range.

        Returns:
            The newly created order (coordinates snapped to grid corners).

        Raises:
            ValueError: If the list does not contain exactly four values.
        """
        if len(values) != 4:
            raise ValueError("an order needs exactly 4 coordinates")
        order = Order((values[0], values[1]), (values[2], values[3]))
        self.orders.append(order)
        logger.info("Created order %s: res=%s cus=%s", order.id, order.res_pos, order.cus_pos)
        return order

    def assign_order(self, order: Order, rider: "Rider") -> None:
        """Bind ``order`` to ``rider`` by updating both sides.

        Args:
            order: Order to assign.
            rider: Rider receiving the order.
        """
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)

    def find_order(self, order_id: int) -> Optional[Order]:
        """Return the order with ``order_id`` or None."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    def completed_orders(self) -> List[Order]:
        """Return all completed orders."""
        return [order for order in self.orders if order.status == COMPLETED]
