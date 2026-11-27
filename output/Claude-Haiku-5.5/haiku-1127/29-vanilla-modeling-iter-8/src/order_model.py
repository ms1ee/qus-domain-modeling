"""Order data model: coordinate conversion, lifecycle and bookkeeping."""

import itertools
import math
from typing import Any, Dict, Optional, Sequence

import globalvar

MIN_COORD = 0
MAX_COORD = 800
CELL_SIZE = 100
GRID_DIMENSION = 8

_order_ids = itertools.count(1)


def to_cell_center(value: int) -> int:
    """Convert a raw coordinate to the centre of its grid cell.

    Implements ``center = (value // 100) * 100 + 50``. The value 800 lies
    on the outer boundary and is mapped into the last cell.

    Args:
        value: Integer coordinate in the range 0-800.

    Returns:
        Centre coordinate of the containing cell.
    """
    cell = min(int(value) // CELL_SIZE, GRID_DIMENSION - 1)
    return cell * CELL_SIZE + CELL_SIZE // 2


def _validate_point(point: Sequence[int]) -> tuple:
    """Validate an (x, y) pair and return it as a tuple of ints.

    Raises:
        ValueError: If the point is malformed or out of range.
    """
    if len(point) != 2:
        raise ValueError(f"point must have two coordinates, got {point!r}")
    x, y = point
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"coordinate {value!r} is not an integer")
        if not MIN_COORD <= value <= MAX_COORD:
            raise ValueError(
                f"coordinate {value} out of range {MIN_COORD}-{MAX_COORD}"
            )
    return int(x), int(y)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        restaurant_x, restaurant_y: Grid-centre coordinates of the restaurant.
        customer_x, customer_y: Grid-centre coordinates of the customer.
        restaurant_pos, customer_pos: Tuples of the centre coordinates.
        status: "pending", "assigned" or "completed".
        rider_id: Identifier of the assigned rider, or None.
        start_time: Tick at which the order was created.
        completion_time: Tick at which the order was delivered, or None.
        distance: Euclidean distance between restaurant and customer.
        time_taken: Ticks from creation to completion, or None.
        route: Planned Route for the assigned rider, or None.
    """

    def __init__(
        self,
        res_pos: Sequence[int],
        cus_pos: Sequence[int],
        start_time: Optional[int] = None,
    ) -> None:
        """Create an order from raw user coordinates.

        Args:
            res_pos: Restaurant position (x, y), range 0-800.
            cus_pos: Customer position (x, y), range 0-800.
            start_time: Creation tick; defaults to the current tick.

        Raises:
            ValueError: If coordinates are invalid.
        """
        res_x, res_y = _validate_point(res_pos)
        cus_x, cus_y = _validate_point(cus_pos)

        self.id: int = next(_order_ids)
        self.restaurant_x = to_cell_center(res_x)
        self.restaurant_y = to_cell_center(res_y)
        self.customer_x = to_cell_center(cus_x)
        self.customer_y = to_cell_center(cus_y)
        self.restaurant_pos = (self.restaurant_x, self.restaurant_y)
        self.customer_pos = (self.customer_x, self.customer_y)

        self.status: str = "pending"
        self.rider_id: Optional[int] = None
        if start_time is None:
            start_time = int(globalvar.get_value("tick", 0) or 0)
        self.start_time: int = int(start_time)
        self.completion_time: Optional[int] = None
        self.distance: float = math.hypot(
            self.customer_x - self.restaurant_x,
            self.customer_y - self.restaurant_y,
        )
        self.time_taken: Optional[int] = None
        self.route = None

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to the rider with ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"

    def complete(self, completion_time: int) -> None:
        """Mark the order as delivered and record efficiency data.

        Args:
            completion_time: Tick at which delivery finished.
        """
        self.completion_time = int(completion_time)
        self.time_taken = self.completion_time - self.start_time
        self.status = "completed"

    @property
    def efficiency(self) -> float:
        """Distance covered per tick of total order time (0 if unknown)."""
        if not self.time_taken:
            return 0.0
        return self.distance / self.time_taken

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": [self.restaurant_x, self.restaurant_y],
            "customer": [self.customer_x, self.customer_y],
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": round(self.distance, 2),
            "time_taken": self.time_taken,
        }

    def __repr__(self) -> str:
        return (
            f"Order(id={self.id}, restaurant={self.restaurant_pos}, "
            f"customer={self.customer_pos}, status={self.status})"
        )
