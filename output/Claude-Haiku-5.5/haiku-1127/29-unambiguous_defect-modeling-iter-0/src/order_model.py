"""Order data model.

An order is created from user coordinates
``[restaurant_x, restaurant_y, customer_x, customer_y]``. The coordinates are
snapped to grid cell centres and the order tracks its own lifecycle:
``pending`` -> ``assigned`` -> ``picking_up`` -> ``delivering`` -> ``completed``.
"""

import itertools

import globalvar
from grid import is_valid_coordinate, to_grid_point, manhattan, MAP_SIZE

_order_ids = itertools.count(1)


def _validate_point(point, label):
    """Validate an (x, y) input pair.

    Args:
        point: Sequence of two values.
        label: Human-readable name used in error messages.

    Returns:
        tuple: Validated ``(x, y)`` integers.

    Raises:
        ValueError: If the point is malformed or out of range.
    """
    try:
        x, y = point
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be an (x, y) pair")
    for value in (x, y):
        if not is_valid_coordinate(value):
            raise ValueError(f"{label} coordinate {value!r} must be an integer in 0-{MAP_SIZE}")
    return int(x), int(y)


class Order:
    """A food delivery order.

    Attributes:
        id (int): Unique order identifier.
        res_pos (tuple): Restaurant grid cell centre (x, y).
        cus_pos (tuple): Customer grid cell centre (x, y).
        start_time (int): Tick at which the order was created.
        completion_time (int | None): Tick at which delivery finished.
        distance (int): Manhattan distance restaurant -> customer.
        time_taken (int | None): Ticks from creation to completion.
        status (str): Lifecycle status string.
        rider_id (int | None): Assigned rider identifier.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order from raw coordinates.

        Args:
            res_pos: Restaurant input point (x, y), 0-800.
            cus_pos: Customer input point (x, y), 0-800.

        Raises:
            ValueError: If either point is malformed or out of range.
        """
        res_x, res_y = _validate_point(res_pos, "restaurant")
        cus_x, cus_y = _validate_point(cus_pos, "customer")
        self.id = next(_order_ids)
        self.res_pos = to_grid_point(res_x, res_y)
        self.cus_pos = to_grid_point(cus_x, cus_y)
        self.start_time = globalvar.get_current_tick()
        self.completion_time = None
        self.distance = manhattan(self.res_pos, self.cus_pos)
        self.time_taken = None
        self.status = "pending"
        self.rider_id = None

    @property
    def coordinates(self):
        """Return the grid coordinates as ``[rx, ry, cx, cy]``."""
        return [self.res_pos[0], self.res_pos[1], self.cus_pos[0], self.cus_pos[1]]

    @property
    def efficiency(self):
        """Return delivery efficiency as distance units per tick (0.0 if unknown)."""
        if not self.time_taken:
            return 0.0
        return round(self.distance / self.time_taken, 2)

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = int(rider_id)
        self.status = "assigned"

    def complete(self, tick=None):
        """Mark the order as delivered and record completion timing.

        Args:
            tick: Completion tick; defaults to the current simulated tick.
        """
        self.completion_time = globalvar.get_current_tick() if tick is None else int(tick)
        self.time_taken = max(0, self.completion_time - self.start_time)
        self.status = "completed"

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "status": self.status,
            "rider_id": self.rider_id,
        }
