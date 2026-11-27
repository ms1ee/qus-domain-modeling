"""Order data model.

An order stores the raw input coordinates, the grid-cell centre points used
for navigation, its lifecycle status and delivery statistics.
"""

import logging
import math
from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from path_planner import MAP_SIZE, to_cell_center

logger = logging.getLogger(__name__)

Point = Tuple[int, int]


def _validate_point(point: Sequence[Any], label: str) -> Point:
    """Validate an ``[x, y]`` pair of integers in the range 0-800.

    Args:
        point: Sequence of two integers.
        label: Human readable name used in error messages.

    Returns:
        A tuple of two ints.

    Raises:
        ValueError: If the format, type or range is invalid.
    """
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise ValueError(f"{label} location must be given as [x, y]")
    values = []
    for value in point:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} coordinates must be integers, got {value!r}")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"{label} coordinates must be in range 0-{MAP_SIZE}, got {value}")
        values.append(value)
    return values[0], values[1]


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        raw_restaurant: Restaurant coordinates as entered by the user.
        raw_customer: Customer coordinates as entered by the user.
        restaurant_x, restaurant_y: Grid-cell centre of the restaurant.
        customer_x, customer_y: Grid-cell centre of the customer.
        status: One of "created", "assigned", "picked_up", "completed".
        rider_id: ID of the assigned rider, or None.
        start_time: Tick at which the order was created.
        pickup_time: Tick at which the rider reached the restaurant.
        completion_time: Tick at which the order was delivered.
        distance: Euclidean distance between restaurant and customer centres.
        time_taken: Ticks between creation and completion.
    """

    STATUS_CREATED = "created"
    STATUS_ASSIGNED = "assigned"
    STATUS_PICKED_UP = "picked_up"
    STATUS_COMPLETED = "completed"

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: [restaurant_x, restaurant_y] (0-800).
            cus_pos: [customer_x, customer_y] (0-800).

        Raises:
            ValueError: If the coordinates are malformed or out of range.
        """
        raw_res = _validate_point(res_pos, "restaurant")
        raw_cus = _validate_point(cus_pos, "customer")
        self.id = globalvar.next_value("order_id_counter")
        self.raw_restaurant = raw_res
        self.raw_customer = raw_cus
        self.restaurant_x, self.restaurant_y = to_cell_center(*raw_res)
        self.customer_x, self.customer_y = to_cell_center(*raw_cus)
        self.status = self.STATUS_CREATED
        self.rider_id: Optional[int] = None
        self.start_time = int(globalvar.get_value("current_tick", 0))
        self.pickup_time: Optional[int] = None
        self.completion_time: Optional[int] = None
        self.distance = float(math.hypot(self.restaurant_x - self.customer_x,
                                         self.restaurant_y - self.customer_y))
        self.time_taken: Optional[int] = None
        logger.debug("Order %d created: %s -> %s", self.id, raw_res, raw_cus)

    @property
    def res_center(self) -> Point:
        """Restaurant grid-cell centre as a tuple."""
        return self.restaurant_x, self.restaurant_y

    @property
    def cus_center(self) -> Point:
        """Customer grid-cell centre as a tuple."""
        return self.customer_x, self.customer_y

    @property
    def efficiency(self) -> Optional[float]:
        """Delivery efficiency in distance units per tick, or None if unfinished."""
        if self.time_taken is None:
            return None
        return round(self.distance / max(self.time_taken, 1), 2)

    def assign_to(self, rider_id: int) -> None:
        """Record the rider assigned to this order.

        The caller is responsible for appending the order to ``rider.orders``.

        Args:
            rider_id: Identifier of the assigned rider.
        """
        self.rider_id = rider_id
        if self.status == self.STATUS_CREATED:
            self.status = self.STATUS_ASSIGNED

    def mark_picked_up(self, tick: int) -> None:
        """Mark that the rider has collected the food at the restaurant.

        Args:
            tick: Current simulation tick.
        """
        self.status = self.STATUS_PICKED_UP
        self.pickup_time = tick

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and compute its statistics.

        Args:
            tick: Current simulation tick.
        """
        self.status = self.STATUS_COMPLETED
        self.completion_time = tick
        self.time_taken = tick - self.start_time
        logger.info("Order %d completed in %d ticks", self.id, self.time_taken)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.raw_restaurant),
            "customer": list(self.raw_customer),
            "restaurant_center": [self.restaurant_x, self.restaurant_y],
            "customer_center": [self.customer_x, self.customer_y],
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "distance": round(self.distance, 2),
            "time_taken": self.time_taken,
        }
