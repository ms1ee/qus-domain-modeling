"""Order data model and coordinate validation."""

import itertools
from typing import Any, Dict, List, Optional, Sequence

import globalvar
from path_planner import MAP_SIZE, cell_center, euclidean

_id_source = itertools.count(1)


def validate_order_coords(values: Sequence[Any]) -> List[int]:
    """Validate the four order coordinates.

    Args:
        values: Sequence ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

    Returns:
        The validated list of four integers.

    Raises:
        ValueError: If the count is wrong, a value is not an integer, or a
            value lies outside 0-800.
    """
    if len(values) != 4:
        raise ValueError("an order needs exactly four coordinates")
    result: List[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"coordinate {value!r} must be an integer")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"coordinate {value} is out of range 0-{MAP_SIZE}")
        result.append(value)
    return result


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order id.
        res_pos: Restaurant grid-cell centre ``(x, y)``.
        cus_pos: Customer grid-cell centre ``(x, y)``.
        status: "pending", "assigned" or "completed".
        rider_id: Id of the assigned rider, or None.
        start_time: Tick at which the order was created.
        completion_time: Tick at which delivery finished, or None.
        distance: Straight-line distance between restaurant and customer.
        time_taken: Ticks from creation to completion, or None.
        efficiency: Distance per tick after completion, or None.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from raw input coordinates.

        Args:
            res_pos: Restaurant ``(x, y)`` in 0-800.
            cus_pos: Customer ``(x, y)`` in 0-800.

        Raises:
            ValueError: If a coordinate is invalid.
        """
        rx, ry, cx, cy = validate_order_coords(list(res_pos) + list(cus_pos))
        self.id = next(_id_source)
        self.res_pos = (cell_center(rx), cell_center(ry))
        self.cus_pos = (cell_center(cx), cell_center(cy))
        self.status = "pending"
        self.rider_id: Optional[int] = None
        self.start_time = int(globalvar.get_value("current_tick", 0))
        self.completion_time: Optional[int] = None
        self.distance = float(euclidean(self.res_pos, self.cus_pos))
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None

    def assign_to(self, rider_id: int) -> None:
        """Record the rider that serves this order.

        Args:
            rider_id: Id of the rider.
        """
        self.rider_id = int(rider_id)
        self.status = "assigned"

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and compute its statistics.

        Args:
            tick: Tick at which delivery finished.
        """
        self.status = "completed"
        self.completion_time = int(tick)
        self.time_taken = max(0, self.completion_time - self.start_time)
        self.efficiency = (self.distance / self.time_taken
                           if self.time_taken > 0 else None)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "status": self.status,
            "rider_id": self.rider_id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": round(self.distance, 2),
            "time_taken": self.time_taken,
            "efficiency": (round(self.efficiency, 3)
                           if self.efficiency is not None else None),
        }

    def __repr__(self) -> str:
        return (f"Order(id={self.id}, res={self.res_pos}, cus={self.cus_pos}, "
                f"status={self.status})")
