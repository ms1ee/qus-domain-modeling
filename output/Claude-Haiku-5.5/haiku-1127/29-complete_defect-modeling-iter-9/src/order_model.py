"""Order data model and coordinate conversion helpers."""

import itertools

from config import CELL_SIZE, GRID_SIZE, MAP_SIZE

_ORDER_ID_COUNTER = itertools.count(1)


def validate_coordinate(value, label: str = "coordinate") -> int:
    """Validate a single integer coordinate in the range 0-800.

    Args:
        value: Candidate coordinate.
        label: Human readable name used in error messages.

    Returns:
        int: The validated coordinate.

    Raises:
        ValueError: If the value is not an integer or is out of range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer, got {value!r}")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"{label} {value} is out of range 0-{MAP_SIZE}")
    return value


def validate_point(point, label: str = "point") -> tuple:
    """Validate an ``[x, y]`` point.

    Args:
        point: Sequence of exactly two integers.
        label: Human readable name used in error messages.

    Returns:
        tuple: ``(x, y)`` as validated integers.

    Raises:
        ValueError: If the point is malformed or out of range.
    """
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise ValueError(f"{label} must be a pair [x, y], got {point!r}")
    return (validate_coordinate(point[0], f"{label} x"),
            validate_coordinate(point[1], f"{label} y"))


def grid_cell_of(point) -> tuple:
    """Return the ``(grid_x, grid_y)`` index of the cell containing a point.

    Points on the far boundary (800) are clamped into the last cell.

    Args:
        point: ``(x, y)`` coordinates in 0-800.

    Returns:
        tuple: Grid indices in 0-7.
    """
    gx = min(point[0] // CELL_SIZE, GRID_SIZE - 1)
    gy = min(point[1] // CELL_SIZE, GRID_SIZE - 1)
    return gx, gy


def to_cell_center(point) -> tuple:
    """Convert a coordinate to the center of its grid cell.

    Uses ``center = (grid // 100) * 100 + 50`` per axis, with boundary
    clamping so that coordinate 800 maps to the last cell center (750).

    Args:
        point: ``(x, y)`` coordinates in 0-800.

    Returns:
        tuple: ``(center_x, center_y)``.
    """
    gx, gy = grid_cell_of(point)
    half = CELL_SIZE // 2
    return gx * CELL_SIZE + half, gy * CELL_SIZE + half


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier (auto-incremented, starting at 1).
        res_pos: Validated restaurant coordinates ``[x, y]``.
        cus_pos: Validated customer coordinates ``[x, y]``.
        restaurant: Grid cell center of the restaurant.
        customer: Grid cell center of the customer.
        status: One of pending, assigned, picking_up, delivering, completed.
        rider_id: Identifier of the assigned rider, or None.
        start_time: Tick at which the order was created.
        completion_time: Tick at which delivery finished, or None.
        distance: Total Manhattan distance travelled for this order.
        time_taken: Ticks between creation and completion, or None.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: Restaurant coordinates ``[x, y]`` (0-800).
            cus_pos: Customer coordinates ``[x, y]`` (0-800).

        Raises:
            ValueError: If either coordinate pair is invalid.
        """
        self.id = next(_ORDER_ID_COUNTER)
        self.res_pos = list(validate_point(res_pos, "restaurant"))
        self.cus_pos = list(validate_point(cus_pos, "customer"))
        self.restaurant = to_cell_center(self.res_pos)
        self.customer = to_cell_center(self.cus_pos)
        self.status = "pending"
        self.rider_id = None
        self.start_time = 0
        self.completion_time = None
        self.distance = 0
        self.time_taken = None

    def assign_to(self, rider_id: int) -> None:
        """Record that this order has been assigned to a rider.

        Args:
            rider_id: Identifier of the assigned rider.
        """
        self.rider_id = int(rider_id)
        self.status = "assigned"

    def mark_picking_up(self) -> None:
        """Mark the order as being picked up by the rider."""
        self.status = "picking_up"

    def mark_delivering(self) -> None:
        """Mark the order as picked up and en route to the customer."""
        self.status = "delivering"

    def mark_completed(self, tick: int) -> None:
        """Mark the order as delivered and record completion statistics.

        Args:
            tick: Simulation tick at which delivery finished.
        """
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = max(0, tick - self.start_time)

    def to_dict(self) -> dict:
        """Serialise the order to a JSON-compatible dictionary.

        Returns:
            dict: Order fields.
        """
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "restaurant": list(self.restaurant),
            "customer": list(self.customer),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self) -> str:
        return f"Order(id={self.id}, status={self.status!r})"
