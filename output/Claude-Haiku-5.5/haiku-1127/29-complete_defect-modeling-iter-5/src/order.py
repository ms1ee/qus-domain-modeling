"""Order assignment and order management.

Provides the rider selection algorithm (closest rider first, with a load
penalty so that busy riders are used only when they are reasonably close)
and the OrderManager that tracks pending and active orders.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Sequence

from config import get_config
from globalvar import get_value
from order_model import Order
from path_planner import manhattan

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional[Any]:
    """Select the best rider for an order.

    The score of a rider is the street distance from its current position to
    the restaurant plus ``load_penalty`` for every order it already carries.
    The rider with the lowest score wins; ties are broken by rider ID.

    Args:
        order: The order that needs a rider.

    Returns:
        The selected Rider, or None when no rider exists.
    """
    riders = get_value("riders") or []
    if not riders:
        return None
    penalty = get_config().load_penalty
    best = None
    best_key = None
    for rider in riders:
        distance = manhattan((rider.x, rider.y), order.restaurant_pos)
        key = (distance + penalty * len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best_key = key
            best = rider
    return best


class OrderManager:
    """Creates orders, assigns them to riders and tracks their status."""

    def create_order(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> Order:
        """Create an order and place it in the pending queue.

        Args:
            res_pos: Restaurant coordinates (x, y).
            cus_pos: Customer coordinates (x, y).

        Returns:
            The newly created Order.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        order = Order(res_pos, cus_pos)
        get_value("orders").append(order)
        get_value("pending_orders").append(order)
        return order

    def assign(self, order: Order, rider: Any) -> None:
        """Assign an order to a rider.

        Args:
            order: The order to assign.
            rider: The rider that receives the order.
        """
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        pending = get_value("pending_orders")
        if order in pending:
            pending.remove(order)

    def assign_pending(self) -> List[Order]:
        """Assign as many pending orders as possible, oldest first.

        Returns:
            The list of orders assigned during this call.
        """
        assigned: List[Order] = []
        for order in list(get_value("pending_orders") or []):
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            self.assign(order, rider)
            assigned.append(order)
        return assigned

    def find_order(self, order_id: int) -> Optional[Order]:
        """Look up an order by its identifier.

        Args:
            order_id: Identifier of the order.

        Returns:
            The matching Order, or None.
        """
        for order in get_value("orders") or []:
            if order.id == order_id:
                return order
        return None
