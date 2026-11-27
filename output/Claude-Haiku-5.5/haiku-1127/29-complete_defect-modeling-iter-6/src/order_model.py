"""Order data model.

An order stores the restaurant and customer locations converted to grid
cell centres, its lifecycle status and its delivery statistics.
"""

import itertools
from typing import Any, Dict, List, Optional, Sequence, Tuple

from grid import CELL_SIZE, GRID_DIMENSION, to_cell_center, validate_coordinate

_ID_SEQUENCE = itertools.count(1)


def _parse_position(position: Sequence[int], label: str) -> Tuple[int, int]:
    """Validate an (x, y) pair and return it as integers.

    Args:
        position: Pair of raw coordinates.
        label: Location name used in error messages.

    Returns:
        Tuple of validated (x, y).

    Raises:
        ValueError: If the pair is malformed or out of range.
    """
    try:
        x, y = position
    except (TypeError, ValueError):
        raise ValueError(f"{label} position must be a pair (x, y)") from None
    return (validate_coordinate(x, f"{label} x"),
            validate_coordinate(y, f"{label} y"))


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        restaurant_x, restaurant_y: Restaurant cell centre.
        customer_x, customer_y: Customer cell centre.
        start_time: Tick at which the order was created.
        completion_time: Tick of delivery, or None.
        distance: Total distance travelled for this order (units).
        time_taken: Ticks from creation to delivery, or None.
        status: "pending", "assigned", "picked_up" or "completed".
        rider_id: Identifier of the assigned rider, or None.
        route_points: Planned route points (restaurant leg then customer
            leg), used for the map display.
    """

    PENDING = "pending"
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    COMPLETED = "completed"

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int],
                 start_time: int = 0) -> None:
        """Create an order from raw restaurant and customer coordinates.

        Args:
            res_pos: Restaurant (x, y) in the range 0-800.
            cus_pos: Customer (x, y) in the range 0-800.
            start_time: Tick at which the order is created.

        Raises:
            ValueError: If a coordinate is invalid.
        """
        rx, ry = _parse_position(res_pos, "restaurant")
        cx, cy = _parse_position(cus_pos, "customer")
        self.id = next(_ID_SEQUENCE)
        self.restaurant_x = to_cell_center(rx)
        self.restaurant_y = to_cell_center(ry)
        self.customer_x = to_cell_center(cx)
        self.customer_y = to_cell_center(cy)
        self.start_time = int(start_time)
        self.completion_time: Optional[int] = None
        self.distance = 0.0
        self.time_taken: Optional[int] = None
        self.status = Order.PENDING
        self.rider_id: Optional[int] = None
        self.route_points: List[Tuple[int, int]] = []

    @property
    def restaurant_pos(self) -> Tuple[int, int]:
        """Restaurant cell centre as (x, y)."""
        return (self.restaurant_x, self.restaurant_y)

    @property
    def customer_pos(self) -> Tuple[int, int]:
        """Customer cell centre as (x, y)."""
        return (self.customer_x, self.customer_y)

    @property
    def efficiency(self) -> float:
        """Distance per tick for a completed order (0.0 if not completed)."""
        if not self.time_taken:
            return 0.0
        return self.distance / self.time_taken

    def restaurant_cell(self) -> Tuple[int, int]:
        """Return the restaurant grid cell indices (column, row)."""
        return (min(self.restaurant_x // CELL_SIZE, GRID_DIMENSION - 1),
                min(self.restaurant_y // CELL_SIZE, GRID_DIMENSION - 1))

    def customer_cell(self) -> Tuple[int, int]:
        """Return the customer grid cell indices (column, row)."""
        return (min(self.customer_x // CELL_SIZE, GRID_DIMENSION - 1),
                min(self.customer_y // CELL_SIZE, GRID_DIMENSION - 1))

    def assign_to(self, rider_id: int) -> None:
        """Record the assigned rider and mark the order as assigned.

        Args:
            rider_id: Identifier of the rider taking the order.
        """
        self.rider_id = int(rider_id)
        self.status = Order.ASSIGNED

    def mark_picked_up(self) -> None:
        """Mark the food as collected at the restaurant."""
        self.status = Order.PICKED_UP

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and record efficiency data.

        Args:
            tick: Tick at which the delivery happened.
        """
        self.completion_time = int(tick)
        self.time_taken = self.completion_time - self.start_time
        self.status = Order.COMPLETED

    def record_route(self, start: Tuple[int, int],
                     waypoints: Sequence[Tuple[int, int]]) -> None:
        """Append planned route points for the map display.

        Args:
            start: Point the leg starts from. Only stored for the first leg.
            waypoints: Waypoints of the leg.
        """
        if not self.route_points:
            self.route_points.append((int(start[0]), int(start[1])))
        self.route_points.extend((int(p[0]), int(p[1])) for p in waypoints)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": [self.restaurant_x, self.restaurant_y],
            "customer": [self.customer_x, self.customer_y],
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": round(self.distance, 2),
            "time_taken": self.time_taken,
            "efficiency": round(self.efficiency, 3),
            "status": self.status,
            "rider_id": self.rider_id,
        }
