"""Order management: creation, rider selection, assignment and recruitment."""

import logging
import math
from typing import List, Optional, Tuple

import globalvar
from order_model import COORD_MAX, COORD_MIN, Order
from rider import Rider
from system import SystemManager

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the best rider for an order.

    The rider with the fewest active orders is preferred; ties are broken by
    the Euclidean distance between the rider and the restaurant,
    sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2).

    Args:
        order: The order that needs a rider.

    Returns:
        The selected Rider, or None if no rider exists.
    """
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None

    def _key(rider: Rider) -> Tuple[int, float, int]:
        distance = math.sqrt(
            (rider.x - order.restaurant_x) ** 2 + (rider.y - order.restaurant_y) ** 2
        )
        return (len(rider.active_orders()), distance, rider.rider_id)

    return min(riders, key=_key)


class OrderManager:
    """Creates orders, dispatches pending orders and tracks their lifecycle."""

    def __init__(self) -> None:
        """Create a manager; state is kept in the global store."""
        self.system = SystemManager()

    @staticmethod
    def validate_coordinates(values: List[int]) -> None:
        """Validate that four coordinates lie in the accepted range.

        Args:
            values: [restaurant_x, restaurant_y, customer_x, customer_y].

        Raises:
            ValueError: If the count is wrong or a value is out of range.
        """
        if len(values) != 4:
            raise ValueError("An order needs exactly four coordinates.")
        for value in values:
            if not COORD_MIN <= value <= COORD_MAX:
                raise ValueError(
                    f"Coordinate {value} is outside the range {COORD_MIN}-{COORD_MAX}."
                )

    def create_order(self, rx: int, ry: int, cx: int, cy: int) -> Order:
        """Create an order and register it in the order list.

        Args:
            rx: Restaurant x coordinate.
            ry: Restaurant y coordinate.
            cx: Customer x coordinate.
            cy: Customer y coordinate.

        Returns:
            The created Order (status "pending").

        Raises:
            ValueError: If any coordinate is invalid.
        """
        self.validate_coordinates([rx, ry, cx, cy])
        order = Order((rx, ry), (cx, cy))
        self.system.orders.append(order)
        return order

    def pending_orders(self) -> List[Order]:
        """Return orders that have not been assigned to any rider yet.

        Returns:
            List of pending Order objects in creation order.
        """
        return [o for o in self.system.orders if o.status == "pending"]

    def dispatch_pending(self) -> Tuple[List[Tuple[Order, Rider]], List[Rider]]:
        """Recruit riders if needed and assign every pending order.

        Returns:
            A tuple (assigned, new_riders) where ``assigned`` holds
            (order, rider) pairs and ``new_riders`` lists riders recruited.
        """
        pending = self.pending_orders()
        if not pending:
            return [], []
        idle = self.system.idle_rider_count()
        new_riders = self.system.recruit_if_needed(len(pending), idle)
        assigned: List[Tuple[Order, Rider]] = []
        for order in pending:
            rider = find_best_rider_for_order(order)
            if rider is None:
                continue
            try:
                order.assign_to(rider.rider_id)
                assigned.append((order, rider))
            except ValueError:
                logger.exception("Failed to assign order %d", order.id)
        return assigned, new_riders

    def submit_order(self, rx: int, ry: int, cx: int, cy: int) -> dict:
        """Create an order and immediately try to assign it.

        Args:
            rx: Restaurant x coordinate.
            ry: Restaurant y coordinate.
            cx: Customer x coordinate.
            cy: Customer y coordinate.

        Returns:
            Dictionary with keys "order" (Order), "rider" (Rider or None) and
            "new_riders" (list of riders recruited during this call).
        """
        order = self.create_order(rx, ry, cx, cy)
        _, new_riders = self.dispatch_pending()
        rider = None
        if order.rider_id is not None:
            rider = self.system.get_rider(order.rider_id)
        return {"order": order, "rider": rider, "new_riders": new_riders}
