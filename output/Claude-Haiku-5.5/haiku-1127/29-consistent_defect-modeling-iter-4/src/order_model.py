"""Order data model and coordinate handling.

An order is described by a restaurant point and a customer point. Input
coordinates are snapped to the top-left corner of their 100x100 grid cell so
that every location lies on a street intersection of the 8x8 grid.
"""

import itertools
from typing import Any, Dict, Optional, Sequence, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = 8
INPUT_MIN = 0
INPUT_MAX = 1000

STATUS_CREATED = "created"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"

_order_ids = itertools.count(1)


def to_grid_corner(value: int) -> int:
    """Snap a coordinate to the top-left corner of its grid cell.

    Values beyond the last cell are clamped to the last cell's corner.

    Args:
        value: Raw coordinate in the range 0-1000.

    Returns:
        The corner coordinate (a multiple of CELL_SIZE, at most 700).
    """
    cell = min(max(int(value), 0) // CELL_SIZE, GRID_DIMENSION - 1)
    return cell * CELL_SIZE


def validate_point(point: Sequence[Any], label: str = "point") -> Tuple[int, int]:
    """Validate a 2-element coordinate pair.

    Args:
        point: Sequence containing x and y.
        label: Human readable name used in error messages.

    Returns:
        A tuple ``(x, y)`` of integers.

    Raises:
        ValueError: If the point is malformed, not integer or out of range.
    """
    if len(point) != 2:
        raise ValueError(f"{label} must contain exactly 2 coordinates")
    result = []
    for value in point:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} coordinates must be integers")
        if not INPUT_MIN <= value <= INPUT_MAX:
            raise ValueError(
                f"{label} coordinate {value} out of range "
                f"{INPUT_MIN}-{INPUT_MAX}"
            )
        result.append(value)
    return result[0], result[1]


def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: First point ``(x, y)``.
        b: Second point ``(x, y)``.

    Returns:
        ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id (int): Unique order identifier.
        restaurant_x, restaurant_y (int): Snapped restaurant grid point.
        customer_x, customer_y (int): Snapped customer grid point.
        start_time (int): Tick at which the order was created.
        completion_time (int | None): Tick at which delivery completed.
        distance (int): Manhattan distance between restaurant and customer.
        time_taken (int | None): Ticks from creation to completion.
        rider_id (int | None): ID of the assigned rider.
        status (str): One of created, assigned, picking_up, delivering,
            completed.
        picked_up_time (int | None): Tick at which the rider reached the
            restaurant.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int],
                 start_time: int = 0) -> None:
        """Create an order from raw input coordinates.

        Args:
            res_pos: Restaurant point ``(x, y)`` in range 0-1000.
            cus_pos: Customer point ``(x, y)`` in range 0-1000.
            start_time: Creation tick.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        res_x, res_y = validate_point(res_pos, "restaurant")
        cus_x, cus_y = validate_point(cus_pos, "customer")
        self.id: int = next(_order_ids)
        self.restaurant_x = to_grid_corner(res_x)
        self.restaurant_y = to_grid_corner(res_y)
        self.customer_x = to_grid_corner(cus_x)
        self.customer_y = to_grid_corner(cus_y)
        self.start_time = int(start_time)
        self.completion_time: Optional[int] = None
        self.distance = manhattan(self.restaurant_pos, self.customer_pos)
        self.time_taken: Optional[int] = None
        self.rider_id: Optional[int] = None
        self.picked_up_time: Optional[int] = None
        self.status = STATUS_CREATED

    @property
    def restaurant_pos(self) -> Tuple[int, int]:
        """Return the restaurant grid point as ``(x, y)``."""
        return self.restaurant_x, self.restaurant_y

    @property
    def customer_pos(self) -> Tuple[int, int]:
        """Return the customer grid point as ``(x, y)``."""
        return self.customer_x, self.customer_y

    @property
    def efficiency(self) -> Optional[float]:
        """Return delivery efficiency (distance units per tick), if completed."""
        if self.time_taken is None:
            return None
        return self.distance / max(self.time_taken, 1)

    def assign_to(self, rider_id: int) -> None:
        """Record the assigned rider and mark the order as assigned.

        Args:
            rider_id: ID of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_accepted(self) -> None:
        """Mark the order as accepted by its rider (pickup in progress)."""
        self.status = STATUS_PICKING_UP

    def mark_picked_up(self, now: int) -> None:
        """Mark arrival at the restaurant.

        Args:
            now: Current simulated tick.
        """
        self.picked_up_time = now
        self.status = STATUS_DELIVERING

    def mark_completed(self, now: int) -> None:
        """Mark the order as delivered and compute timing data.

        Args:
            now: Current simulated tick.
        """
        self.completion_time = now
        self.time_taken = now - self.start_time
        self.status = STATUS_COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
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
            "efficiency": self.efficiency,
        }
