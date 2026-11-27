"""Order data model.

An Order records a restaurant pickup and a customer drop-off. User input is
in the range 0-800 and is converted to grid cell centers on creation.
"""

import itertools
from typing import Any, Dict, Sequence, Tuple

import globalvar
from path_planner import MAP_SIZE, Grid

_GRID = Grid()
_id_source = itertools.count(1)

STATUS_CREATED = "created"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_REJECTED = "rejected"
FINISHED_STATUSES = (STATUS_COMPLETED, STATUS_FAILED, STATUS_REJECTED)


def to_grid_center(value: int) -> int:
    """Convert a coordinate to its grid cell center.

    Implements ``center = (value // 100) * 100 + 50``, clamped to the map.
    """
    return _GRID.cell_center(value)


def _validate_point(pos: Sequence[int]) -> Tuple[int, int]:
    """Validate an ``(x, y)`` input pair and return it as ints.

    Raises:
        ValueError: If the pair is malformed, not integer, or out of range.
    """
    if len(pos) != 2:
        raise ValueError("a location needs exactly two coordinates (x, y)")
    values = []
    for value in pos:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"coordinate must be an integer, got {value!r}")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"coordinate {value} is outside the range 0-{MAP_SIZE}")
        values.append(value)
    return values[0], values[1]


def _current_tick() -> int:
    """Return the current simulated tick from the global store."""
    return int(globalvar.get_value("current_tick", 0) or 0)


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        status: One of created, assigned, picking_up, delivering, completed,
            failed or rejected.
        raw_restaurant: Restaurant coordinates as entered by the user.
        raw_customer: Customer coordinates as entered by the user.
        restaurant_x, restaurant_y: Restaurant grid cell center.
        customer_x, customer_y: Customer grid cell center.
        rider_id: ID of the assigned rider, or None.
        start_time: Tick at which the order was created.
        completion_time: Tick at which the order was delivered, or None.
        distance: Planned travel distance in coordinate units.
        time_taken: Ticks from creation to completion, or None.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: ``(restaurant_x, restaurant_y)`` in range 0-800.
            cus_pos: ``(customer_x, customer_y)`` in range 0-800.

        Raises:
            ValueError: If a coordinate is invalid.
        """
        rx, ry = _validate_point(res_pos)
        cx, cy = _validate_point(cus_pos)
        self.id = next(_id_source)
        self.raw_restaurant = (rx, ry)
        self.raw_customer = (cx, cy)
        self.restaurant_x = to_grid_center(rx)
        self.restaurant_y = to_grid_center(ry)
        self.customer_x = to_grid_center(cx)
        self.customer_y = to_grid_center(cy)
        self.status = STATUS_CREATED
        self.rider_id = None
        self.start_time = _current_tick()
        self.completion_time = None
        self.distance = 0
        self.time_taken = None

    @property
    def restaurant_pos(self) -> Tuple[int, int]:
        """Restaurant grid center as an ``(x, y)`` tuple."""
        return (self.restaurant_x, self.restaurant_y)

    @property
    def customer_pos(self) -> Tuple[int, int]:
        """Customer grid center as an ``(x, y)`` tuple."""
        return (self.customer_x, self.customer_y)

    def assign_to(self, rider_id: int) -> None:
        """Record the rider this order is assigned to.

        The caller is responsible for appending the order to ``rider.orders``.
        """
        self.rider_id = rider_id
        if self.status == STATUS_CREATED:
            self.status = STATUS_ASSIGNED

    def set_status(self, status: str) -> None:
        """Set the lifecycle status of the order."""
        self.status = status

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and compute its delivery time."""
        self.status = STATUS_COMPLETED
        self.completion_time = tick
        self.time_taken = tick - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "status": self.status,
            "restaurant": list(self.raw_restaurant),
            "customer": list(self.raw_customer),
            "restaurant_cell": list(self.restaurant_pos),
            "customer_cell": list(self.customer_pos),
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
