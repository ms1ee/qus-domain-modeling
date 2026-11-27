"""Order data model.

An order stores the raw restaurant and customer coordinates entered by the
user, together with their grid cell centres used for routing.
"""

from __future__ import annotations

import itertools
import logging
from typing import Any, Dict, Optional, Sequence, Tuple

from globalvar import get_value
from path_planner import GridMap, manhattan

logger = logging.getLogger(__name__)

_ORDER_IDS = itertools.count(1)


def validate_point(point: Sequence[Any]) -> Tuple[int, int]:
    """Validate a user supplied coordinate pair.

    Args:
        point: Sequence of two integers (x, y).

    Returns:
        The validated (x, y) tuple.

    Raises:
        ValueError: If the point is malformed, not integer, or out of range.
    """
    if len(point) != 2:
        raise ValueError("a point needs exactly two coordinates")
    grid = GridMap.from_config()
    values = []
    for value in point:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("coordinates must be integers")
        values.append(value)
    x, y = values
    if not grid.in_range(x, y):
        raise ValueError(f"coordinates must be within 0-{grid.map_size}")
    return x, y


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        restaurant_raw: Raw restaurant coordinates entered by the user.
        customer_raw: Raw customer coordinates entered by the user.
        restaurant_pos: Grid cell centre of the restaurant.
        customer_pos: Grid cell centre of the customer.
        start_time: Tick at which the order was created.
        distance: Street distance between restaurant and customer, in cells.
        rider_id: ID of the assigned rider, or None.
        status: "pending", "assigned" or "completed".
        completion_time: Tick at which the order was delivered, or None.
        time_taken: Ticks between creation and delivery, or None.
        efficiency: Distance covered per tick for the delivery, or None.
    """

    STATUS_PENDING = "pending"
    STATUS_ASSIGNED = "assigned"
    STATUS_COMPLETED = "completed"

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create a new order from raw coordinates.

        Args:
            res_pos: Restaurant coordinates (x, y), range 0-800.
            cus_pos: Customer coordinates (x, y), range 0-800.

        Raises:
            ValueError: If either coordinate pair is invalid.
        """
        grid = GridMap.from_config()
        self.id = next(_ORDER_IDS)
        self.restaurant_raw = validate_point(res_pos)
        self.customer_raw = validate_point(cus_pos)
        self.restaurant_pos = grid.snap(*self.restaurant_raw)
        self.customer_pos = grid.snap(*self.customer_raw)
        self.start_time = int(get_value("current_tick", 0) or 0)
        self.distance = manhattan(self.restaurant_pos, self.customer_pos) / grid.cell_size
        self.rider_id: Optional[int] = None
        self.status = self.STATUS_PENDING
        self.completion_time: Optional[int] = None
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None
        logger.info("Order #%d created: restaurant %s, customer %s",
                    self.id, self.restaurant_pos, self.customer_pos)

    def assign_to(self, rider_id: int) -> None:
        """Record that the order has been assigned to a rider.

        The caller is responsible for appending the order to rider.orders.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = self.STATUS_ASSIGNED
        logger.info("Order #%d assigned to rider #%d", self.id, rider_id)

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and record its efficiency data.

        Args:
            tick: Simulated time at which delivery finished.
        """
        self.status = self.STATUS_COMPLETED
        self.completion_time = int(tick)
        self.time_taken = max(int(tick) - self.start_time, 0)
        if self.time_taken > 0:
            self.efficiency = self.distance / self.time_taken
        else:
            self.efficiency = self.distance
        logger.info("Order #%d completed at tick %d", self.id, tick)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order.

        Returns:
            Dictionary with the order attributes.
        """
        return {
            "id": self.id,
            "start_time": self.start_time,
            "restaurant": list(self.restaurant_pos),
            "customer": list(self.customer_pos),
            "distance": round(self.distance, 4),
            "rider_id": self.rider_id,
            "status": self.status,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "efficiency": None if self.efficiency is None else round(self.efficiency, 6),
        }
