"""Order data model.

An order is described by ``[restaurant_x, restaurant_y, customer_x, customer_y]``.
Input coordinates are converted to grid cell centers on creation.
"""

import itertools
import math
from typing import Any, Dict, Optional, Sequence, Tuple

from grid import to_grid_center

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_COMPLETED = "completed"

_ORDER_IDS = itertools.count(1)


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        restaurant_x: Restaurant X (grid cell center).
        restaurant_y: Restaurant Y (grid cell center).
        customer_x: Customer X (grid cell center).
        customer_y: Customer Y (grid cell center).
        start_time: Tick at which the order was created.
        completion_time: Tick at which delivery finished, or None.
        distance: Euclidean distance between restaurant and customer.
        time_taken: Ticks between creation and completion, or None.
        rider_id: Identifier of the assigned rider, or None.
        status: "pending", "assigned" or "completed".
    """

    def __init__(
        self,
        res_pos: Sequence[int],
        cus_pos: Sequence[int],
        start_time: int = 0,
    ) -> None:
        """Create an order from raw input points.

        Args:
            res_pos: Restaurant point ``(x, y)`` in the range 0-800.
            cus_pos: Customer point ``(x, y)`` in the range 0-800.
            start_time: Creation tick.

        Raises:
            ValueError: If a point has the wrong shape or invalid coordinates.
        """
        res_x, res_y = _parse_point(res_pos, "restaurant")
        cus_x, cus_y = _parse_point(cus_pos, "customer")
        self.id: int = next(_ORDER_IDS)
        self.restaurant_x, self.restaurant_y = to_grid_center(res_x, res_y)
        self.customer_x, self.customer_y = to_grid_center(cus_x, cus_y)
        self.start_time: int = int(start_time)
        self.completion_time: Optional[int] = None
        self.distance: float = round(
            math.hypot(self.customer_x - self.restaurant_x, self.customer_y - self.restaurant_y),
            2,
        )
        self.time_taken: Optional[int] = None
        self.rider_id: Optional[int] = None
        self.status: str = STATUS_PENDING

    @property
    def res_pos(self) -> Tuple[int, int]:
        """Restaurant grid point as a tuple."""
        return self.restaurant_x, self.restaurant_y

    @property
    def cus_pos(self) -> Tuple[int, int]:
        """Customer grid point as a tuple."""
        return self.customer_x, self.customer_y

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to the rider with ``rider_id``.

        Args:
            rider_id: Identifier of the rider.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_completed(self, tick: int) -> None:
        """Record delivery completion and release the order.

        Args:
            tick: Simulation tick at which the delivery finished.
        """
        self.completion_time = int(tick)
        self.time_taken = self.completion_time - self.start_time
        self.status = STATUS_COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order.

        Returns:
            Dictionary with the order's attributes.
        """
        return {
            "id": self.id,
            "status": self.status,
            "restaurant": [self.restaurant_x, self.restaurant_y],
            "customer": [self.customer_x, self.customer_y],
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "rider_id": self.rider_id,
        }


def _parse_point(point: Sequence[int], label: str) -> Tuple[int, int]:
    """Validate that ``point`` is a pair of integers.

    Args:
        point: Candidate point.
        label: Human readable name used in error messages.

    Returns:
        Tuple ``(x, y)``.

    Raises:
        ValueError: If the point does not have exactly two integer values.
    """
    if len(point) != 2:
        raise ValueError(f"{label} point must contain exactly two coordinates")
    x, y = point
    return x, y
