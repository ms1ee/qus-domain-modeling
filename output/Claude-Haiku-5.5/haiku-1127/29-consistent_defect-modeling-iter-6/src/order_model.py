"""Order data model with coordinate normalisation and lifecycle tracking."""

import itertools
import logging
from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from grid_map import GridMap

logger = logging.getLogger(__name__)

ORDER_PENDING = "pending"
ORDER_ASSIGNED = "assigned"
ORDER_PICKING_UP = "picking_up"
ORDER_DELIVERING = "delivering"
ORDER_COMPLETED = "completed"

_GRID = GridMap()
_ORDER_IDS = itertools.count(1)


def normalize_position(pos: Sequence[int]) -> Tuple[int, int]:
    """Validate an input coordinate pair and snap it to its grid cell.

    Args:
        pos: Pair ``(x, y)`` with integer values in the range 0-800.

    Returns:
        The top-left corner of the containing grid cell.

    Raises:
        ValueError: If the pair is malformed, non-integer or out of range.
    """
    try:
        x, y = pos
    except (TypeError, ValueError):
        raise ValueError("position must be a pair (x, y)")
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"coordinate {value!r} is not an integer")
        if not 0 <= value <= _GRID.map_size:
            raise ValueError(f"coordinate {value} is out of range 0-{_GRID.map_size}")
    return _GRID.snap_point((x, y))


class Order:
    """A food delivery order from a restaurant to a customer."""

    def __init__(
        self,
        res_pos: Sequence[int],
        cus_pos: Sequence[int],
        start_time: Optional[int] = None,
    ) -> None:
        """Create an order.

        Args:
            res_pos: Restaurant coordinates ``(x, y)`` in 0-800.
            cus_pos: Customer coordinates ``(x, y)`` in 0-800.
            start_time: Creation tick. Defaults to the current simulated time.

        Raises:
            ValueError: If either position is invalid.
        """
        self.id: int = next(_ORDER_IDS)
        self.restaurant_x, self.restaurant_y = normalize_position(res_pos)
        self.customer_x, self.customer_y = normalize_position(cus_pos)
        if start_time is None:
            start_time = int(globalvar.get_value("current_time", 0) or 0)
        self.start_time: int = start_time
        self.completion_time: Optional[int] = None
        self.distance: float = float(
            abs(self.customer_x - self.restaurant_x)
            + abs(self.customer_y - self.restaurant_y)
        )
        self.time_taken: int = 0
        self.rider_id: Optional[int] = None
        self.assigned_time: Optional[int] = None
        self.status: str = ORDER_PENDING

    @property
    def restaurant_pos(self) -> Tuple[int, int]:
        """Restaurant grid point."""
        return (self.restaurant_x, self.restaurant_y)

    @property
    def customer_pos(self) -> Tuple[int, int]:
        """Customer grid point."""
        return (self.customer_x, self.customer_y)

    @property
    def efficiency(self) -> float:
        """Delivery efficiency: distance covered per tick (0.0 if not completed)."""
        if self.time_taken <= 0:
            return 0.0
        return self.distance / self.time_taken

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to the rider with ``rider_id``."""
        self.rider_id = rider_id
        self.status = ORDER_ASSIGNED
        self.assigned_time = int(globalvar.get_value("current_time", 0) or 0)

    def complete(self, completion_time: int) -> None:
        """Mark the order as delivered and record completion statistics.

        Args:
            completion_time: Tick at which the customer received the order.
        """
        self.completion_time = int(completion_time)
        self.time_taken = self.completion_time - self.start_time
        self.status = ORDER_COMPLETED
        logger.info(
            "order %d completed at t=%d (time_taken=%d)",
            self.id, self.completion_time, self.time_taken,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the order."""
        return {
            "id": self.id,
            "restaurant": [self.restaurant_x, self.restaurant_y],
            "customer": [self.customer_x, self.customer_y],
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "rider_id": self.rider_id,
            "status": self.status,
        }

    def __repr__(self) -> str:
        return (
            f"Order(id={self.id}, restaurant={self.restaurant_pos}, "
            f"customer={self.customer_pos}, status={self.status})"
        )
