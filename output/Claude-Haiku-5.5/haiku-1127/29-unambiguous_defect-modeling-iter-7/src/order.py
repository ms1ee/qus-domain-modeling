"""Order management and distance-first rider assignment."""

from typing import TYPE_CHECKING, List, Optional, Sequence

import globalvar
from order_model import Order

if TYPE_CHECKING:  # pragma: no cover
    from rider import Rider

DISTANCE_WEIGHT = 1
LOAD_PENALTY = 200  # Distance-equivalent penalty per active order (load balancing).


def find_best_rider_for_order(order: Order) -> "Rider":
    """Select the most suitable rider for an order.

    The score is the Manhattan distance from the rider to the restaurant plus a
    load penalty per already assigned order. The lowest score wins; ties are
    broken by the smaller rider ID.

    Args:
        order: Order that needs a rider.

    Returns:
        Rider: The chosen rider, or None when no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    rx, ry = order.res_pos
    best = None
    best_score = None
    for rider in riders:
        distance = abs(rider.x - rx) + abs(rider.y - ry)
        score = (
            DISTANCE_WEIGHT * distance + LOAD_PENALTY * len(rider.orders),
            rider.rider_id,
        )
        if best_score is None or score < best_score:
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        orders: All orders created during the session.
    """

    def __init__(self) -> None:
        """Create an empty order manager."""
        self.orders: List[Order] = []

    def create_order(self, res_pos: Sequence[int], cus_pos: Sequence[int], tick: int = 0) -> Order:
        """Create and register a new order.

        Args:
            res_pos: Restaurant coordinates.
            cus_pos: Customer coordinates.
            tick: Current simulated tick.

        Returns:
            Order: The newly created order.
        """
        order = Order(res_pos, cus_pos, start_time=tick)
        self.orders.append(order)
        return order

    def assign_order(self, order: Order) -> Optional["Rider"]:
        """Assign a pending order to the best rider.

        Args:
            order: A pending order.

        Returns:
            Rider: The rider now responsible for the order, or None if no
            rider is available.

        Raises:
            ValueError: If the order is not pending.
        """
        if order.status != "pending":
            raise ValueError(f"order {order.id} is already {order.status}")
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider

    def discard(self, order: Order) -> None:
        """Remove a pending order that could not be assigned.

        Args:
            order: Order to remove.

        Returns:
            None
        """
        if order in self.orders and order.status == "pending":
            self.orders.remove(order)

    def active_orders(self) -> List[Order]:
        """Return orders that are not yet completed.

        Returns:
            List[Order]: Active orders.
        """
        return [order for order in self.orders if not order.is_completed()]

    def completed_orders(self) -> List[Order]:
        """Return delivered orders.

        Returns:
            List[Order]: Completed orders.
        """
        return [order for order in self.orders if order.is_completed()]

    def find(self, order_id: int) -> Optional[Order]:
        """Look up an order by identifier.

        Args:
            order_id: Order identifier.

        Returns:
            Order: Matching order or None.
        """
        for order in self.orders:
            if order.id == order_id:
                return order
        return None
