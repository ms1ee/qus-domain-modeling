"""Order data model: coordinate conversion, lifecycle and efficiency data."""

import logging

import globalvar
from path_planner import (manhattan, snap_to_center, validate_coordinate)

logger = logging.getLogger(__name__)

DELIVERY_FEE = 100


def _parse_point(point, label):
    """Validate a ``(x, y)`` pair given by the user.

    Args:
        point: Sequence of exactly two integers.
        label: Name used in error messages.

    Returns:
        Tuple of the two validated integers.

    Raises:
        ValueError: If the sequence length is wrong or a value is out of range.
        TypeError: If a value is not an integer.
    """
    if len(point) != 2:
        raise ValueError(f"{label} position must have exactly 2 coordinates")
    x = validate_coordinate(point[0], f"{label} x")
    y = validate_coordinate(point[1], f"{label} y")
    return x, y


class Order:
    """A food delivery order from a restaurant to a customer.

    The input format is ``[restaurant_x, restaurant_y, customer_x, customer_y]``
    split into two points. Stored positions are converted to grid cell centres.

    Attributes:
        id (int): Unique order identifier.
        status (str): "created", "assigned", "picking_up", "delivering", or
            "completed".
        rider_id (int or None): Assigned rider identifier.
        raw_res_pos (tuple): Restaurant position as entered by the user.
        raw_cus_pos (tuple): Customer position as entered by the user.
        res_pos (tuple): Restaurant grid cell centre.
        cus_pos (tuple): Customer grid cell centre.
        distance (int): Manhattan distance restaurant -> customer.
        fee (int): Income credited on delivery.
        start_time (int): Tick at which the order was created.
        assigned_time (int or None): Tick at which the order was assigned.
        completion_time (int or None): Tick at which delivery finished.
    """

    _counter = 0

    def __init__(self, res_pos, cus_pos):
        """Create an order from restaurant and customer positions.

        Args:
            res_pos: Sequence ``[x, y]`` of the restaurant location (0-800).
            cus_pos: Sequence ``[x, y]`` of the customer location (0-800).

        Raises:
            ValueError: If coordinates are out of range or malformed.
            TypeError: If coordinates are not integers.
        """
        raw_res = _parse_point(res_pos, "restaurant")
        raw_cus = _parse_point(cus_pos, "customer")
        Order._counter += 1
        self.id = Order._counter
        self.raw_res_pos = raw_res
        self.raw_cus_pos = raw_cus
        self.res_pos = (snap_to_center(raw_res[0]), snap_to_center(raw_res[1]))
        self.cus_pos = (snap_to_center(raw_cus[0]), snap_to_center(raw_cus[1]))
        self.status = "created"
        self.rider_id = None
        self.fee = DELIVERY_FEE
        self.distance = manhattan(self.res_pos, self.cus_pos)
        self.start_time = globalvar.get_value("tick", 0)
        self.assigned_time = None
        self.completion_time = None

    @property
    def time_taken(self):
        """Return ticks from creation to completion, or None if unfinished."""
        if self.completion_time is None:
            return None
        return self.completion_time - self.start_time

    @property
    def efficiency(self):
        """Return delivery efficiency (distance per tick), or None."""
        taken = self.time_taken
        if not taken:
            return None
        return self.distance / taken

    def assign_to(self, rider_id):
        """Record that the order has been assigned to ``rider_id``.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = "assigned"
        self.assigned_time = globalvar.get_value("tick", 0)

    def complete(self, tick):
        """Mark the order as delivered at ``tick``.

        Args:
            tick: Simulated time of delivery.
        """
        self.status = "completed"
        self.completion_time = tick
        logger.info("Order #%s completed at tick %s", self.id, tick)

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the order."""
        return {
            "id": self.id,
            "status": self.status,
            "rider_id": self.rider_id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "distance": self.distance,
            "fee": self.fee,
            "start_time": self.start_time,
            "assigned_time": self.assigned_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
        }
