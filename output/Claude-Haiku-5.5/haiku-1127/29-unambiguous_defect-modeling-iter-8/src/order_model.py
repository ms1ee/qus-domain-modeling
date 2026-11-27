"""Order data model: validation, coordinate snapping and lifecycle."""

import itertools
from typing import Any, Dict, Sequence

import globalvar
from grid_map import MAP_SIZE, Point, snap_point

_ORDER_IDS = itertools.count(1)


def _current_tick() -> int:
    """Return the current simulation tick from the global store."""
    return globalvar.get_value("current_tick") or 0


def _validate_point(point: Sequence[int]) -> Point:
    """Validate a raw (x, y) pair.

    Args:
        point: Two integers in the range 0-800.

    Returns:
        The validated (x, y) tuple.

    Raises:
        TypeError: If a value is not an integer.
        ValueError: If the pair has the wrong length or is out of range.
    """
    if len(point) != 2:
        raise ValueError("a point must contain exactly two coordinates")
    x, y = point
    for value in (x, y):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"coordinate {value!r} is not an integer")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"coordinate {value} is outside 0-{MAP_SIZE}")
    return int(x), int(y)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Snapped restaurant grid cell centre (x, y).
        cus_pos: Snapped customer grid cell centre (x, y).
        coordinates: [restaurant_x, restaurant_y, customer_x, customer_y].
        start_time: Tick at which the order was created.
        completion_time: Tick at which the order was delivered, or None.
        distance: Planned route distance in map units.
        time_taken: Ticks between creation and completion, or None.
        status: created, assigned, picking_up, delivering, completed or
            rejected.
        rider_id: Identifier of the assigned rider, or None.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and snap its coordinates to grid cell centres.

        Args:
            res_pos: Restaurant position as (x, y), each in 0-800.
            cus_pos: Customer position as (x, y), each in 0-800.

        Raises:
            TypeError: If a coordinate is not an integer.
            ValueError: If a coordinate is out of range.
        """
        rx, ry = _validate_point(res_pos)
        cx, cy = _validate_point(cus_pos)
        self.id = next(_ORDER_IDS)
        self.raw_restaurant = (rx, ry)
        self.raw_customer = (cx, cy)
        self.res_pos: Point = snap_point(rx, ry)
        self.cus_pos: Point = snap_point(cx, cy)
        self.coordinates = [self.res_pos[0], self.res_pos[1],
                            self.cus_pos[0], self.cus_pos[1]]
        self.start_time = _current_tick()
        self.completion_time = None
        self.distance = 0.0
        self.time_taken = None
        self.status = "created"
        self.rider_id = None

    def assign_to(self, rider_id: int) -> None:
        """Assign the order to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self) -> None:
        """Mark the order as delivered and record completion data."""
        tick = _current_tick()
        self.completion_time = tick
        self.time_taken = tick - self.start_time
        self.status = "completed"

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order.

        Returns:
            Dictionary with the order attributes.
        """
        return {
            "id": self.id,
            "coordinates": list(self.coordinates),
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": round(float(self.distance), 2),
            "time_taken": self.time_taken,
            "status": self.status,
            "rider_id": self.rider_id,
        }
