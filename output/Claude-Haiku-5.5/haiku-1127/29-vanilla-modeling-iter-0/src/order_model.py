"""Order data model: coordinate validation, grid conversion and lifecycle."""

import itertools
from typing import Any, Dict, Sequence, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = MAP_SIZE // CELL_SIZE

_order_ids = itertools.count(1)


def validate_coordinate(value: Any, name: str = "coordinate") -> int:
    """Validate that a coordinate is an integer within 0-800.

    Args:
        value: Value to validate.
        name: Label used in error messages.

    Returns:
        The validated integer.

    Raises:
        TypeError: If the value is not an integer.
        ValueError: If the value is outside 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {value!r}")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"{name} must be within 0-{MAP_SIZE}, got {value}")
    return value


def to_grid_center(value: int) -> int:
    """Convert a coordinate to the center of its grid cell.

    Implements ``center = (value // 100) * 100 + 50``. Values at the far
    boundary (800) are clamped into the last cell so that the center stays
    inside the map.

    Args:
        value: Coordinate in units (0-800).

    Returns:
        The cell center coordinate along that axis.
    """
    index = min(max(value // CELL_SIZE, 0), GRID_CELLS - 1)
    return index * CELL_SIZE + CELL_SIZE // 2


def _parse_point(point: Sequence[int], label: str) -> Tuple[int, int]:
    """Validate a two-element (x, y) point and return it as integers."""
    if len(point) != 2:
        raise ValueError(f"{label} must contain exactly 2 coordinates")
    return (validate_coordinate(point[0], f"{label}_x"),
            validate_coordinate(point[1], f"{label}_y"))


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        restaurant_x: Grid-center x of the restaurant.
        restaurant_y: Grid-center y of the restaurant.
        customer_x: Grid-center x of the customer.
        customer_y: Grid-center y of the customer.
        status: "created", "assigned" or "completed".
        rider_id: ID of the assigned rider, or None.
        start_time: Simulated tick at which the order was created.
        completion_time: Simulated tick of delivery, or None.
        time_taken: Ticks between creation and delivery, or None.
        distance: Route length (Manhattan distance along streets).
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int],
                 start_time: int = 0) -> None:
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: Restaurant (x, y) in the range 0-800.
            cus_pos: Customer (x, y) in the range 0-800.
            start_time: Simulated tick of creation.

        Raises:
            TypeError: If a coordinate is not an integer.
            ValueError: If a coordinate is out of range or malformed.
        """
        rx, ry = _parse_point(res_pos, "restaurant")
        cx, cy = _parse_point(cus_pos, "customer")
        self.id = next(_order_ids)
        self.restaurant_x = to_grid_center(rx)
        self.restaurant_y = to_grid_center(ry)
        self.customer_x = to_grid_center(cx)
        self.customer_y = to_grid_center(cy)
        self.status = "created"
        self.rider_id = None
        self.start_time = int(start_time)
        self.completion_time = None
        self.time_taken = None
        self.distance = float(abs(self.restaurant_x - self.customer_x)
                              + abs(self.restaurant_y - self.customer_y))

    @property
    def restaurant_pos(self) -> Tuple[int, int]:
        """Restaurant grid-center coordinates as a tuple."""
        return self.restaurant_x, self.restaurant_y

    @property
    def customer_pos(self) -> Tuple[int, int]:
        """Customer grid-center coordinates as a tuple."""
        return self.customer_x, self.customer_y

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.

        Raises:
            RuntimeError: If the order is already completed.
        """
        if self.status == "completed":
            raise RuntimeError(f"Order {self.id} is already completed")
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, completion_time: int) -> None:
        """Mark the order as delivered and record efficiency data.

        Args:
            completion_time: Simulated tick at which delivery finished.
        """
        self.status = "completed"
        self.completion_time = int(completion_time)
        self.time_taken = self.completion_time - self.start_time

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
            "time_taken": self.time_taken,
            "distance": self.distance,
        }
