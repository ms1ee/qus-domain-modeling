"""Order data model and coordinate conversion."""

import itertools

import globalvar
from constants import (
    CELL_SIZE,
    GRID_DIM,
    MAP_SIZE,
    ORDER_ASSIGNED,
    ORDER_COMPLETED,
    ORDER_PENDING,
)

_ORDER_IDS = itertools.count(1)


def validate_point(x, y):
    """Validate that ``x`` and ``y`` are integers inside the map.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Raises:
        ValueError: If a value is not an integer or is outside 0..MAP_SIZE.
    """
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("coordinates must be integers")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"coordinate {value} is out of range 0-{MAP_SIZE}")


def to_cell_center(x, y):
    """Convert an input coordinate to the centre point of its grid cell.

    Uses ``center = (value // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2``.
    Coordinates equal to MAP_SIZE belong to the last cell.

    Args:
        x: X coordinate in 0..MAP_SIZE.
        y: Y coordinate in 0..MAP_SIZE.

    Returns:
        tuple[int, int]: Cell centre (cx, cy).
    """
    validate_point(x, y)
    cx = min(x // CELL_SIZE, GRID_DIM - 1) * CELL_SIZE + CELL_SIZE // 2
    cy = min(y // CELL_SIZE, GRID_DIM - 1) * CELL_SIZE + CELL_SIZE // 2
    return cx, cy


class Order:
    """A delivery order from a restaurant to a customer.

    Attributes:
        id (int): Unique order identifier.
        res_pos (tuple[int, int]): Restaurant cell centre.
        cus_pos (tuple[int, int]): Customer cell centre.
        input_res (tuple[int, int]): Restaurant coordinate as entered.
        input_cus (tuple[int, int]): Customer coordinate as entered.
        status (str): One of pending/assigned/picking_up/delivering/completed.
        rider_id (int | None): Assigned rider identifier.
        start_time (int): Tick when the order was created.
        pickup_time (int | None): Tick when the rider reached the restaurant.
        completion_time (int | None): Tick when delivery completed.
        distance (int): Manhattan distance between restaurant and customer centres.
        time_taken (int | None): Ticks from creation to completion.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: Sequence [restaurant_x, restaurant_y] (0-800).
            cus_pos: Sequence [customer_x, customer_y] (0-800).

        Raises:
            ValueError: If the input is malformed or out of range.
        """
        res = self._validate_pair(res_pos, "restaurant")
        cus = self._validate_pair(cus_pos, "customer")
        self.id = next(_ORDER_IDS)
        self.input_res = res
        self.input_cus = cus
        self.res_pos = to_cell_center(*res)
        self.cus_pos = to_cell_center(*cus)
        self.status = ORDER_PENDING
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0)
        self.pickup_time = None
        self.completion_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))
        self.time_taken = None

    @staticmethod
    def _validate_pair(pos, label):
        """Validate an (x, y) pair and return it as a tuple of ints."""
        try:
            x, y = pos
        except (TypeError, ValueError):
            raise ValueError(f"{label} location must contain exactly two values")
        validate_point(x, y)
        return int(x), int(y)

    def assign_to(self, rider_id):
        """Record the rider this order is assigned to.

        The caller is responsible for appending the order to ``rider.orders``.

        Args:
            rider_id: Identifier of the assigned rider.
        """
        self.rider_id = rider_id
        if self.status == ORDER_PENDING:
            self.status = ORDER_ASSIGNED

    def mark_picked_up(self, time):
        """Record arrival at the restaurant.

        Args:
            time: Current simulation tick.
        """
        from constants import ORDER_DELIVERING
        self.pickup_time = time
        self.status = ORDER_DELIVERING

    def mark_completed(self, time):
        """Record delivery completion and compute the time taken.

        Args:
            time: Current simulation tick.
        """
        self.completion_time = time
        self.time_taken = max(time - self.start_time, 0)
        self.status = ORDER_COMPLETED

    @property
    def efficiency(self):
        """Delivery efficiency in distance units per tick, or None if unfinished."""
        if not self.time_taken:
            return None
        return round(self.distance / self.time_taken, 2)

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.input_res),
            "customer": list(self.input_cus),
            "restaurant_center": list(self.res_pos),
            "customer_center": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self):
        return f"Order(id={self.id}, status={self.status}, rider={self.rider_id})"
