"""Order data model: coordinate normalisation and order lifecycle."""

import itertools
import math

MAP_MIN = 0
MAP_MAX = 800
CELL_SIZE = 100
GRID_CELLS = 8

_order_ids = itertools.count(1)


class OrderValidationError(ValueError):
    """Raised when order coordinates are malformed or out of range."""


def validate_coordinate(value):
    """Validate that a coordinate is an integer within 0-800.

    Args:
        value: Candidate coordinate.

    Returns:
        The validated integer.

    Raises:
        OrderValidationError: If the value is not an int or is out of range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise OrderValidationError(f"Coordinate must be an integer, got {value!r}.")
    if not MAP_MIN <= value <= MAP_MAX:
        raise OrderValidationError(
            f"Coordinate {value} is out of range ({MAP_MIN}-{MAP_MAX})."
        )
    return value


def to_grid_center(value):
    """Convert one axis coordinate to the centre of its grid cell.

    Uses ``center = (value // 100) * 100 + 50``; the value 800 is mapped to
    the last cell so the centre stays inside the map.

    Args:
        value: Validated axis coordinate.

    Returns:
        Centre coordinate of the containing cell.
    """
    cell = min(value // CELL_SIZE, GRID_CELLS - 1)
    return cell * CELL_SIZE + CELL_SIZE // 2


def to_grid_point(pos):
    """Convert an ``(x, y)`` input position to its grid cell centre.

    Args:
        pos: Sequence of two integers in range 0-800.

    Returns:
        Tuple ``(center_x, center_y)``.

    Raises:
        OrderValidationError: If the position is malformed or out of range.
    """
    try:
        x, y = pos
    except (TypeError, ValueError):
        raise OrderValidationError(f"Position must contain exactly two values, got {pos!r}.")
    return (
        to_grid_center(validate_coordinate(x)),
        to_grid_center(validate_coordinate(y)),
    )


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        restaurant: Restaurant grid-cell centre ``(x, y)``.
        customer: Customer grid-cell centre ``(x, y)``.
        start_time: Tick at which the order was created.
        status: One of ``pending``, ``assigned``, ``completed``.
        rider_id: Identifier of the assigned rider, or None.
        completion_time: Tick at which delivery finished, or None.
        time_taken: Ticks between creation and completion, or None.
        distance: Euclidean distance between restaurant and customer.
        delivery_efficiency: Distance per tick after completion, or None.
    """

    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"

    def __init__(self, res_pos, cus_pos, start_time=0):
        """Create an order and normalise its coordinates.

        Args:
            res_pos: Restaurant ``(x, y)`` input in range 0-800.
            cus_pos: Customer ``(x, y)`` input in range 0-800.
            start_time: Tick at creation time.

        Raises:
            OrderValidationError: If any coordinate is invalid.
        """
        self.id = next(_order_ids)
        self.restaurant = to_grid_point(res_pos)
        self.customer = to_grid_point(cus_pos)
        self.start_time = int(start_time)
        self.status = Order.PENDING
        self.rider_id = None
        self.completion_time = None
        self.time_taken = None
        self.distance = math.hypot(
            self.customer[0] - self.restaurant[0],
            self.customer[1] - self.restaurant[1],
        )
        self.delivery_efficiency = None

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = Order.ASSIGNED

    def complete(self, tick):
        """Mark the order as delivered and compute efficiency data.

        Args:
            tick: Simulation tick at which delivery finished.
        """
        self.status = Order.COMPLETED
        self.completion_time = int(tick)
        self.time_taken = max(0, self.completion_time - self.start_time)
        if self.time_taken > 0:
            self.delivery_efficiency = self.distance / self.time_taken
        else:
            self.delivery_efficiency = self.distance

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.restaurant),
            "customer": list(self.customer),
            "start_time": self.start_time,
            "status": self.status,
            "rider_id": self.rider_id,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "delivery_efficiency": self.delivery_efficiency,
        }
