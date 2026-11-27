"""Order data model.

An order is created from ``[restaurant_x, restaurant_y, customer_x,
customer_y]`` user input. Coordinates are validated (0-800, integers) and
converted to grid cell-center points.
"""

from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from path_planner import MAP_SIZE, Point, manhattan, to_cell_point


def _validate_point(point: Sequence[int], label: str) -> Tuple[int, int]:
    """Validate a raw ``(x, y)`` pair.

    Args:
        point: Two-element sequence of integers.
        label: Name used in error messages.

    Returns:
        Validated ``(x, y)`` tuple.

    Raises:
        ValueError: If the pair does not have two elements or is out of range.
        TypeError: If a coordinate is not an integer.
    """
    try:
        x, y = point
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{label} position must contain exactly two coordinates") from exc
    values = []
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                f"{label} coordinates must be integers, got {value!r}")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(
                f"{label} coordinate {value} is outside 0-{MAP_SIZE}")
        values.append(value)
    return values[0], values[1]


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        restaurant_raw: Raw restaurant coordinates as entered by the user.
        customer_raw: Raw customer coordinates as entered by the user.
        res_pos: Restaurant grid cell-center point.
        cus_pos: Customer grid cell-center point.
        status: "pending", "assigned", "pickup", "delivering" or "completed".
        rider_id: ID of the assigned rider, or None.
        start_time: Tick when the order was created.
        completed_time: Tick when delivery finished, or None.
        distance: Manhattan street distance between restaurant and customer.
        duration: Ticks taken from creation to completion, or None.
        fee: Amount charged to the customer when the order is placed.
    """

    _counter = 0

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create and validate a new order.

        Args:
            res_pos: ``(restaurant_x, restaurant_y)``, integers in 0-800.
            cus_pos: ``(customer_x, customer_y)``, integers in 0-800.

        Raises:
            ValueError: On malformed or out-of-range coordinates.
            TypeError: On non-integer coordinates.
        """
        self.restaurant_raw = _validate_point(res_pos, "Restaurant")
        self.customer_raw = _validate_point(cus_pos, "Customer")

        Order._counter += 1
        self.id: int = Order._counter

        self.res_pos: Point = to_cell_point(*self.restaurant_raw)
        self.cus_pos: Point = to_cell_point(*self.customer_raw)

        config = globalvar.get_value("config") or {}
        self.fee: int = int(config.get("order_fee", 150))
        self.status: str = "pending"
        self.rider_id: Optional[int] = None
        self.start_time: int = int(globalvar.get_value("tick", 0) or 0)
        self.completed_time: Optional[int] = None
        self.distance: int = manhattan(self.res_pos, self.cus_pos)
        self.duration: Optional[int] = None

    def assign_to(self, rider_id: int) -> None:
        """Record the rider this order is assigned to.

        The caller is responsible for appending the order to the rider's
        ``orders`` list.

        Args:
            rider_id: ID of the rider receiving the order.
        """
        self.rider_id = int(rider_id)
        self.status = "assigned"

    def mark_completed(self, tick: int) -> None:
        """Mark the order as delivered and record completion data.

        Args:
            tick: Simulated tick at which delivery finished.
        """
        self.completed_time = int(tick)
        self.duration = max(0, self.completed_time - self.start_time)
        self.status = "completed"

    @property
    def efficiency(self) -> Optional[float]:
        """Return delivery efficiency in distance units per tick.

        Returns:
            ``distance / max(duration, 1)``, or None if not yet completed.
        """
        if self.duration is None:
            return None
        return round(self.distance / max(self.duration, 1), 2)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the order.

        Returns:
            Dictionary with all order attributes.
        """
        return {
            "id": self.id,
            "restaurant": list(self.restaurant_raw),
            "customer": list(self.customer_raw),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completed_time": self.completed_time,
            "distance": self.distance,
            "duration": self.duration,
            "fee": self.fee,
            "efficiency": self.efficiency,
        }
