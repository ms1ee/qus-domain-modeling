"""Order data model with coordinate conversion and lifecycle tracking."""

import itertools
import logging
import math

from globalvar import get_value
from grid_map import is_valid_coordinate, to_cell_center

logger = logging.getLogger(__name__)

_ORDER_IDS = itertools.count(1)


def _parse_position(pos, label):
    """Validate a (x, y) pair and return it as integers.

    Args:
        pos: Sequence of two integers in the range 0-800.
        label: Human-readable name used in error messages.

    Raises:
        ValueError: If the pair is malformed or out of range.
    """
    try:
        x, y = pos
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a pair of coordinates") from exc
    for value in (x, y):
        if not is_valid_coordinate(value):
            raise ValueError(
                f"{label} coordinate {value} is out of range 0-800")
    return int(x), int(y)


class Order:
    """A food delivery order.

    Attributes:
        id: Unique integer order number.
        raw_restaurant: Restaurant coordinates as entered by the user.
        raw_customer: Customer coordinates as entered by the user.
        restaurant_x, restaurant_y: Grid-center restaurant location.
        customer_x, customer_y: Grid-center customer location.
        start_time: Tick at which the order was created.
        completion_time: Tick of delivery, or None.
        distance: Euclidean distance between restaurant and customer.
        time_taken: Ticks from creation to delivery, or None.
        rider_id: Assigned rider id, or None.
        status: "pending", "assigned" or "completed".
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order and convert coordinates to grid centers.

        Args:
            res_pos: (x, y) restaurant coordinates (0-800).
            cus_pos: (x, y) customer coordinates (0-800).

        Raises:
            ValueError: If a coordinate is malformed or out of range.
        """
        raw_rx, raw_ry = _parse_position(res_pos, "restaurant")
        raw_cx, raw_cy = _parse_position(cus_pos, "customer")
        self.id = next(_ORDER_IDS)
        self.raw_restaurant = (raw_rx, raw_ry)
        self.raw_customer = (raw_cx, raw_cy)
        self.restaurant_x = to_cell_center(raw_rx)
        self.restaurant_y = to_cell_center(raw_ry)
        self.customer_x = to_cell_center(raw_cx)
        self.customer_y = to_cell_center(raw_cy)
        self.start_time = get_value("current_tick", 0)
        self.completion_time = None
        self.distance = math.hypot(self.customer_x - self.restaurant_x,
                                   self.customer_y - self.restaurant_y)
        self.time_taken = None
        self.rider_id = None
        self.status = "pending"
        logger.info("Order %d created: restaurant (%d, %d) customer (%d, %d)",
                    self.id, self.restaurant_x, self.restaurant_y,
                    self.customer_x, self.customer_y)

    def assign_to(self, rider_id):
        """Mark the order as assigned to the rider with ``rider_id``.

        Args:
            rider_id: Identifier of the rider receiving the order.

        Raises:
            ValueError: If the order is already completed.
        """
        if self.status == "completed":
            raise ValueError(f"order {self.id} is already completed")
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, tick):
        """Mark the order delivered and record completion data.

        Args:
            tick: Simulation tick at which delivery happened.
        """
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = tick - self.start_time
        logger.info("Order %d completed at tick %d", self.id, tick)

    @property
    def efficiency(self):
        """Distance covered per tick for a completed order, else None."""
        if self.status != "completed" or not self.time_taken:
            return None
        return self.distance / self.time_taken

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the order."""
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
