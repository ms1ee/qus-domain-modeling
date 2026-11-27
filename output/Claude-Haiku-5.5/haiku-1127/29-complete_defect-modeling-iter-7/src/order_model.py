"""Order data model: validated coordinates, grid centres and lifecycle data."""

import itertools

import globalvar
from config import CONFIG
from path_planner import PathPlanner

_ID_SEQUENCE = itertools.count(1)


def _current_tick():
    """Return the current simulated tick."""
    return int(globalvar.get_value("tick", 0) or 0)


def _validate_coordinate(value, label):
    """Validate that ``value`` is an integer within the map range.

    Raises:
        TypeError: If the value is not an integer.
        ValueError: If the value is outside 0..map_size.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if not 0 <= value <= CONFIG["map_size"]:
        raise ValueError(f"{label} must be between 0 and {CONFIG['map_size']}")
    return value


def _parse_point(point, label):
    """Validate a (x, y) pair."""
    if len(point) != 2:
        raise ValueError(f"{label} position must contain exactly two coordinates")
    x = _validate_coordinate(point[0], f"{label} x")
    y = _validate_coordinate(point[1], f"{label} y")
    return x, y


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        restaurant_x, restaurant_y: Raw restaurant coordinates.
        customer_x, customer_y: Raw customer coordinates.
        restaurant_center: Grid-cell centre of the restaurant.
        customer_center: Grid-cell centre of the customer.
        status: One of "created", "unassigned", "assigned", "picking_up",
            "delivering", "completed".
        rider_id: Identifier of the assigned rider, or None.
        start_time: Tick at which the order was assigned.
        completion_time: Tick at which delivery completed.
        distance: Distance travelled by the rider while serving the order.
        time_taken: completion_time - start_time once completed.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order.

        Args:
            res_pos: (x, y) restaurant position, each in 0..map_size.
            cus_pos: (x, y) customer position, each in 0..map_size.
        """
        rx, ry = _parse_point(res_pos, "restaurant")
        cx, cy = _parse_point(cus_pos, "customer")
        self.id = next(_ID_SEQUENCE)
        self.restaurant_x = rx
        self.restaurant_y = ry
        self.customer_x = cx
        self.customer_y = cy
        self.restaurant_center = (PathPlanner.grid_center(rx), PathPlanner.grid_center(ry))
        self.customer_center = (PathPlanner.grid_center(cx), PathPlanner.grid_center(cy))
        self.status = "created"
        self.rider_id = None
        self.start_time = None
        self.completion_time = None
        self.distance = 0
        self.time_taken = None

    @property
    def coordinates(self):
        """Return the input format ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.restaurant_x, self.restaurant_y, self.customer_x, self.customer_y]

    def assign_to(self, rider_id, now=None):
        """Mark the order as assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
            now: Optional tick; defaults to the current simulated tick.
        """
        self.rider_id = rider_id
        self.status = "assigned"
        self.start_time = _current_tick() if now is None else now

    def complete(self, now=None):
        """Mark the order as delivered and compute efficiency data.

        Args:
            now: Optional completion tick; defaults to the current tick.
        """
        completion = _current_tick() if now is None else now
        start = self.start_time if self.start_time is not None else completion
        self.completion_time = completion
        self.time_taken = completion - start
        self.status = "completed"

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the order."""
        return {
            "id": self.id,
            "coordinates": self.coordinates,
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
