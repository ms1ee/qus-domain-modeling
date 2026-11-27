"""Order data model.

An order is described by a restaurant location and a customer location. Both
input coordinates are converted to the top-left corner of their grid cell.
"""

import itertools
from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from config import (CELL_SIZE, COORD_MAX, COORD_MIN, MAP_SIZE,
                    ORDER_ASSIGNED, ORDER_COMPLETED, ORDER_PENDING)

_ORDER_IDS = itertools.count(1)


def snap_to_grid(value: int) -> int:
    """Convert a coordinate to the top-left corner of its grid cell.

    Abnormal values are clamped into the map range first.

    Args:
        value: Raw coordinate value.

    Returns:
        The grid-aligned coordinate, a multiple of ``CELL_SIZE``.
    """
    clamped = min(max(int(value), 0), MAP_SIZE)
    return (clamped // CELL_SIZE) * CELL_SIZE


def _validate_point(point: Sequence[Any], label: str) -> Tuple[int, int]:
    """Validate an ``(x, y)`` pair of integers within the allowed range.

    Args:
        point: Sequence containing two integer coordinates.
        label: Human-readable name used in error messages.

    Raises:
        ValueError: If the point is malformed, non-integer, or out of range.
    """
    try:
        values = list(point)
    except TypeError as exc:
        raise ValueError(f"{label} location must be a pair of coordinates.") from exc
    if len(values) != 2:
        raise ValueError(f"{label} location must contain exactly two coordinates.")
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} coordinates must be integers, got {value!r}.")
        if not COORD_MIN <= value <= COORD_MAX:
            raise ValueError(
                f"{label} coordinate {value} is outside the range "
                f"{COORD_MIN}-{COORD_MAX}.")
    return values[0], values[1]


def _current_time() -> int:
    """Return the current simulated time, defaulting to 0."""
    now = globalvar.get_value("simulated_time")
    return now if now is not None else 0


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Grid-aligned restaurant ``(x, y)``.
        cus_pos: Grid-aligned customer ``(x, y)``.
        rider_id: ID of the assigned rider, or None.
        status: One of ``"pending"``, ``"assigned"``, ``"completed"``.
        start_time: Simulated tick at which the order was created.
        completion_time: Simulated tick of delivery, or None.
        distance: Distance travelled by the rider for this order.
        time_taken: Ticks between creation and completion, or None.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: Restaurant ``(x, y)`` in the range 0-800.
            cus_pos: Customer ``(x, y)`` in the range 0-800.

        Raises:
            ValueError: If either location is invalid.
        """
        res_x, res_y = _validate_point(res_pos, "Restaurant")
        cus_x, cus_y = _validate_point(cus_pos, "Customer")
        self.id = next(_ORDER_IDS)
        self.res_pos = (snap_to_grid(res_x), snap_to_grid(res_y))
        self.cus_pos = (snap_to_grid(cus_x), snap_to_grid(cus_y))
        self.rider_id: Optional[int] = None
        self.status = ORDER_PENDING
        self.start_time = _current_time()
        self.completion_time: Optional[int] = None
        self.distance = 0
        self.time_taken: Optional[int] = None

    @classmethod
    def from_list(cls, values: Sequence[int]) -> "Order":
        """Create an order from ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Raises:
            ValueError: If the list does not have exactly four valid integers.
        """
        if len(values) != 4:
            raise ValueError("An order requires exactly four coordinates.")
        return cls((values[0], values[1]), (values[2], values[3]))

    def assign_to(self, rider_id: int) -> None:
        """Record the rider this order is assigned to.

        Args:
            rider_id: Identifier of the rider receiving the order.

        Raises:
            ValueError: If the order has already been completed.
        """
        if self.status == ORDER_COMPLETED:
            raise ValueError(f"Order {self.id} is already completed.")
        self.rider_id = rider_id
        self.status = ORDER_ASSIGNED

    def complete(self, completion_time: int) -> None:
        """Mark the order as delivered and record efficiency data.

        Args:
            completion_time: Simulated tick at which delivery finished.
        """
        self.completion_time = completion_time
        self.time_taken = max(0, completion_time - self.start_time)
        self.status = ORDER_COMPLETED

    @property
    def efficiency(self) -> Optional[float]:
        """Distance covered per tick for a completed order, or None."""
        if not self.time_taken:
            return None
        return round(self.distance / self.time_taken, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "rider_id": self.rider_id,
            "status": self.status,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
