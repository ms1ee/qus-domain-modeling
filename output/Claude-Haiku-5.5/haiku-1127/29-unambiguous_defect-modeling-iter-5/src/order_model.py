"""Order data model with coordinate normalization."""

import itertools

from path_planner import PathPlanner, manhattan, MAP_SIZE

STATUS_CREATED = "created"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"

_PLANNER = PathPlanner()
_order_ids = itertools.count(1)


def _parse_point(point, label):
    """Validate a raw ``[x, y]`` point supplied by the user.

    Args:
        point: Sequence of two integers.
        label: Name used in error messages.

    Returns:
        Tuple ``(x, y)`` of integers.

    Raises:
        ValueError: If the point is malformed or out of range.
    """
    try:
        x, y = point
    except (TypeError, ValueError):
        raise ValueError(f"{label} location must contain exactly two coordinates")
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} coordinates must be integers")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(
                f"{label} coordinates must be between 0 and {MAP_SIZE}, got {value}")
    return x, y


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id (int): Unique order identifier.
        restaurant_x, restaurant_y (int): Snapped restaurant intersection.
        customer_x, customer_y (int): Snapped customer intersection.
        raw_restaurant (tuple): Restaurant point as entered by the user.
        raw_customer (tuple): Customer point as entered by the user.
        start_time (int): Simulated time when the order was created.
        completion_time (int | None): Simulated time of delivery.
        distance (int): Manhattan distance from restaurant to customer.
        time_taken (int | None): Ticks from creation to delivery.
        rider_id (int | None): Assigned rider identifier.
        status (str): Lifecycle status, ``"completed"`` after delivery.
    """

    def __init__(self, res_pos, cus_pos, start_time=0):
        """Create an order and normalize its coordinates.

        Args:
            res_pos: Restaurant point ``[x, y]`` with values in 0..800.
            cus_pos: Customer point ``[x, y]`` with values in 0..800.
            start_time: Simulated time at creation.

        Raises:
            ValueError: If either point is malformed or out of range.
        """
        raw_res = _parse_point(res_pos, "restaurant")
        raw_cus = _parse_point(cus_pos, "customer")
        self.id = next(_order_ids)
        self.raw_restaurant = raw_res
        self.raw_customer = raw_cus
        self.restaurant_x, self.restaurant_y = _PLANNER.snap(*raw_res)
        self.customer_x, self.customer_y = _PLANNER.snap(*raw_cus)
        self.start_time = start_time
        self.completion_time = None
        self.distance = manhattan(self.restaurant_pos, self.customer_pos)
        self.time_taken = None
        self.rider_id = None
        self.status = STATUS_CREATED

    @property
    def order_id(self):
        """Alias for :attr:`id`."""
        return self.id

    @property
    def restaurant_pos(self):
        """Return the snapped restaurant position as ``(x, y)``."""
        return self.restaurant_x, self.restaurant_y

    @property
    def customer_pos(self):
        """Return the snapped customer position as ``(x, y)``."""
        return self.customer_x, self.customer_y

    @property
    def efficiency(self):
        """Return delivery distance per tick, or 0.0 if not yet completed."""
        if not self.time_taken:
            return 0.0
        return self.distance / self.time_taken

    def assign_to(self, rider_id):
        """Record the rider this order has been assigned to.

        Args:
            rider_id: Identifier of the assigned rider.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def complete(self, time):
        """Mark the order as delivered and record timing data.

        Args:
            time: Simulated time of delivery.
        """
        self.completion_time = time
        self.time_taken = time - self.start_time
        self.status = STATUS_COMPLETED

    def to_dict(self):
        """Return a JSON-serializable representation of the order."""
        return {
            "id": self.id,
            "restaurant": [self.restaurant_x, self.restaurant_y],
            "customer": [self.customer_x, self.customer_y],
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "rider_id": self.rider_id,
            "status": self.status,
        }
