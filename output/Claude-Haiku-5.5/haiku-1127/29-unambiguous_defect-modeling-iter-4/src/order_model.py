"""Order data model and coordinate normalization."""

import itertools

import globalvar

MAP_SIZE = 800
CELL_SIZE = 100

_id_counter = itertools.count(1)


def snap_coordinate(value):
    """Convert a raw coordinate to the nearest street intersection.

    Args:
        value: Integer coordinate in the range 0-800.

    Returns:
        Integer multiple of 100 within 0-800.

    Raises:
        TypeError: If ``value`` is not an integer.
        ValueError: If ``value`` is outside 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"Coordinate must be an integer, got {value!r}.")
    if value < 0 or value > MAP_SIZE:
        raise ValueError(f"Coordinate {value} is outside the range 0-{MAP_SIZE}.")
    snapped = ((value + CELL_SIZE // 2) // CELL_SIZE) * CELL_SIZE
    return min(max(snapped, 0), MAP_SIZE)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id (int): Unique order identifier.
        restaurant_pos (tuple[int, int]): Snapped pickup location.
        customer_pos (tuple[int, int]): Snapped delivery location.
        status (str): "pending", "assigned", "picking_up", "delivering",
            or "completed".
        rider_id (int | None): Assigned rider identifier.
        start_time (int): Tick at which the order was created.
        completion_time (int | None): Tick at which the order was delivered.
        distance (int): Manhattan distance between restaurant and customer.
        time_taken (int | None): Ticks between creation and completion.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order and normalize its coordinates.

        Args:
            res_pos: ``(x, y)`` restaurant coordinates in 0-800.
            cus_pos: ``(x, y)`` customer coordinates in 0-800.
        """
        self.id = next(_id_counter)
        self.restaurant_pos = (snap_coordinate(res_pos[0]), snap_coordinate(res_pos[1]))
        self.customer_pos = (snap_coordinate(cus_pos[0]), snap_coordinate(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0)
        self.completion_time = None
        self.distance = (
            abs(self.restaurant_pos[0] - self.customer_pos[0])
            + abs(self.restaurant_pos[1] - self.customer_pos[1])
        )
        self.time_taken = None

    def assign_to(self, rider_id):
        """Record that this order was assigned to the rider ``rider_id``."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, tick):
        """Mark the order as delivered at ``tick`` and compute time taken."""
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = tick - self.start_time

    def to_dict(self):
        """Return a JSON-serializable snapshot of the order."""
        return {
            "id": self.id,
            "restaurant_pos": list(self.restaurant_pos),
            "customer_pos": list(self.customer_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
