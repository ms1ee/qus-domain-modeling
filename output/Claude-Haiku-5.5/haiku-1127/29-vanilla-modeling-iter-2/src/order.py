"""Order management and the closest-rider assignment algorithm."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

import globalvar
from order_model import Order, validate_order_coords
from path_planner import euclidean

if TYPE_CHECKING:  # pragma: no cover - only for type checkers
    from rider import Rider

logger = logging.getLogger(__name__)

# Extra distance-equivalent penalty per order already queued on a rider.
# It spreads load across riders while keeping distance as the main criterion.
LOAD_PENALTY = 100.0


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        pending: Orders not yet assigned to a rider.
        orders: Every order created in this session (history).
    """

    def __init__(self) -> None:
        """Create an empty order manager."""
        self.pending: List[Order] = []
        self.orders: List[Order] = []

    def create_order(self, coords: Sequence[Any]) -> Order:
        """Create an order from ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Args:
            coords: Four integer coordinates in 0-800.

        Returns:
            The newly created pending order.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        values = validate_order_coords(list(coords))
        order = Order((values[0], values[1]), (values[2], values[3]))
        self.pending.append(order)
        self.orders.append(order)
        logger.info("Created order %d", order.id)
        return order

    def pending_count(self) -> int:
        """Return the number of unassigned orders."""
        return len(self.pending)

    def assign(self, order: Order, rider: "Rider") -> None:
        """Assign ``order`` to ``rider``.

        Args:
            order: Pending order.
            rider: Rider that will serve the order.

        Raises:
            ValueError: If the order is already completed.
        """
        if order.status == "completed":
            raise ValueError(f"order {order.id} is already completed")
        rider.add_order(order)
        order.assign_to(rider.rider_id)
        if order in self.pending:
            self.pending.remove(order)
        logger.info("Assigned order %d to rider %d", order.id, rider.rider_id)

    def active_orders(self) -> List[Order]:
        """Return orders that have not been completed yet."""
        return [order for order in self.orders if order.status != "completed"]

    def completed_orders(self) -> List[Order]:
        """Return orders that have been delivered."""
        return [order for order in self.orders if order.status == "completed"]

    def to_dicts(self) -> List[Dict[str, Any]]:
        """Return all orders as JSON-serialisable dictionaries."""
        return [order.to_dict() for order in self.orders]


def find_best_rider_for_order(order: Order) -> Optional["Rider"]:
    """Select the best rider for an order.

    The score is the Euclidean distance from the rider to the restaurant,
    ``sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)``, plus a
    load penalty per already-assigned order. Ties keep the earlier rider.

    Args:
        order: Order that needs a rider.

    Returns:
        The selected rider, or None if no rider exists.
    """
    riders = globalvar.get_value("riders", []) or []
    best: Optional["Rider"] = None
    best_score: Optional[float] = None
    for rider in riders:
        distance = euclidean((rider.x, rider.y), order.res_pos)
        score = distance + LOAD_PENALTY * len(rider.orders)
        if best_score is None or score < best_score:
            best = rider
            best_score = score
    return best
