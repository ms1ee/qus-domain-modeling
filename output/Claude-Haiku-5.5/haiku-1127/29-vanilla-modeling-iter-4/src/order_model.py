"""Order data model.

An order is created from a restaurant position and a customer position,
both given as ``[x, y]`` in the 0-800 range. Both positions are converted
to the centre point of their grid cells.
"""

import itertools
import logging

import globalvar
from path_planner import GridMap, validate_point

logger = logging.getLogger(__name__)

_ORDER_IDS = itertools.count(1)


def _parse_point(point, label):
    """Validate an ``[x, y]`` pair and return it as an int tuple.

    Args:
        point: Sequence of two values.
        label: Name used in error messages (e.g. "restaurant").

    Returns:
        Tuple ``(x, y)`` of ints.

    Raises:
        ValueError: If the sequence length or coordinate values are invalid.
    """
    try:
        x, y = point
    except (TypeError, ValueError):
        raise ValueError(f"{label} position must be a pair [x, y]") from None
    try:
        return validate_point(x, y)
    except ValueError as exc:
        raise ValueError(f"{label} position: {exc}") from None


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        restaurant_x: Restaurant cell-centre X coordinate.
        restaurant_y: Restaurant cell-centre Y coordinate.
        customer_x: Customer cell-centre X coordinate.
        customer_y: Customer cell-centre Y coordinate.
        status: One of ``pending``, ``assigned``, ``picking_up``,
            ``delivering``, ``completed``.
        rider_id: ID of the assigned rider, or None.
        start_time: Tick at which the order was created.
        completion_time: Tick at which delivery finished, or None.
        distance: Total travelled distance attributed to the order.
        time_taken: Ticks from creation to completion, or None.
    """

    PENDING = "pending"
    ASSIGNED = "assigned"
    PICKING_UP = "picking_up"
    DELIVERING = "delivering"
    COMPLETED = "completed"

    def __init__(self, res_pos, cus_pos, start_time=None):
        """Create an order from restaurant and customer positions.

        Args:
            res_pos: Restaurant position ``[x, y]`` (0-800).
            cus_pos: Customer position ``[x, y]`` (0-800).
            start_time: Creation tick. Defaults to the current global tick.

        Raises:
            ValueError: If a position is malformed or out of range.
        """
        res_x, res_y = _parse_point(res_pos, "restaurant")
        cus_x, cus_y = _parse_point(cus_pos, "customer")
        self.id = next(_ORDER_IDS)
        self.restaurant_x, self.restaurant_y = GridMap.center_of(res_x, res_y)
        self.customer_x, self.customer_y = GridMap.center_of(cus_x, cus_y)
        self.status = self.PENDING
        self.rider_id = None
        if start_time is None:
            start_time = globalvar.get_value("current_time", 0)
        self.start_time = start_time
        self.completion_time = None
        self.distance = 0.0
        self.time_taken = None

    @property
    def restaurant_pos(self):
        """Return the restaurant cell-centre as a tuple ``(x, y)``."""
        return (self.restaurant_x, self.restaurant_y)

    @property
    def customer_pos(self):
        """Return the customer cell-centre as a tuple ``(x, y)``."""
        return (self.customer_x, self.customer_y)

    @property
    def efficiency(self):
        """Return distance per tick for a completed order (0.0 otherwise)."""
        if not self.time_taken:
            return 0.0
        return self.distance / self.time_taken

    def assign_to(self, rider_id):
        """Mark the order as assigned to the rider with ``rider_id``.

        Args:
            rider_id: Identifier of the rider taking the order.
        """
        self.rider_id = rider_id
        if self.status == self.PENDING:
            self.status = self.ASSIGNED

    def set_status(self, status):
        """Set the lifecycle status of the order.

        Args:
            status: New status string.
        """
        self.status = status

    def add_distance(self, distance):
        """Add travelled distance to the order.

        Args:
            distance: Distance in units.
        """
        self.distance += distance

    def complete(self, completion_time):
        """Mark the order as delivered and record timing data.

        Args:
            completion_time: Tick at which the delivery finished.
        """
        self.completion_time = completion_time
        self.time_taken = completion_time - self.start_time
        self.status = self.COMPLETED
        logger.info("Order %d completed at tick %d (took %d ticks)",
                    self.id, completion_time, self.time_taken)

    def to_dict(self):
        """Return a JSON-serialisable representation of the order.

        Returns:
            Dictionary of order attributes.
        """
        return {
            "id": self.id,
            "restaurant": [self.restaurant_x, self.restaurant_y],
            "customer": [self.customer_x, self.customer_y],
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": round(self.distance, 2),
            "time_taken": self.time_taken,
        }
