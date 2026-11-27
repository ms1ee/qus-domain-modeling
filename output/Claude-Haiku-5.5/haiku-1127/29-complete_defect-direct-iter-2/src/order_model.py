"""Order data model.

An order holds the restaurant (pickup) and customer (drop-off) locations,
converted to grid cell centers, together with its lifecycle state and
timing records.
"""

import logging

import globalvar
from config import COORD_MAX, COORD_MIN
from path_planner import manhattan, to_cell_center

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _next_order_id():
    """Return the next unique order identifier.

    Returns:
        Positive integer ID.
    """
    value = (globalvar.get_value("order_id_counter") or 0) + 1
    globalvar.set_value("order_id_counter", value)
    return value


def _validate_point(point):
    """Validate a raw ``[x, y]`` coordinate pair.

    Args:
        point: Sequence of two integers in 0..800.

    Returns:
        Tuple ``(x, y)`` of ints.

    Raises:
        ValueError: If the point is malformed or out of range.
    """
    if len(point) != 2:
        raise ValueError("a location needs exactly two coordinates")
    x_val, y_val = point
    for value in (x_val, y_val):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"coordinate {value!r} is not an integer")
        if not COORD_MIN <= value <= COORD_MAX:
            raise ValueError(f"coordinate {value} is outside "
                             f"{COORD_MIN}-{COORD_MAX}")
    return (x_val, y_val)


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        status: One of "pending", "assigned", "picking_up", "delivering",
            or "completed".
        res_pos: Restaurant pickup point (grid cell center).
        cus_pos: Customer drop-off point (grid cell center).
        rider_id: Identifier of the assigned rider, or None.
        start_tick: Tick at which the order was created.
        picked_up_tick: Tick at which the rider reached the restaurant.
        completed_tick: Tick at which the order was delivered.
        distance: Street distance between the two grid centers.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: ``[restaurant_x, restaurant_y]`` integers in 0..800.
            cus_pos: ``[customer_x, customer_y]`` integers in 0..800.

        Raises:
            ValueError: If either location is malformed or out of range.
        """
        self.raw_restaurant = _validate_point(res_pos)
        self.raw_customer = _validate_point(cus_pos)
        self.id = _next_order_id()
        self.res_pos = to_cell_center(*self.raw_restaurant)
        self.cus_pos = to_cell_center(*self.raw_customer)
        self.status = STATUS_PENDING
        self.rider_id = None
        self.start_tick = globalvar.get_value("tick") or 0
        self.picked_up_tick = None
        self.completed_tick = None
        self.distance = manhattan(self.res_pos, self.cus_pos)
        logger.debug("Order #%d created: %s -> %s", self.id,
                     self.res_pos, self.cus_pos)

    def assign_to(self, rider_id):
        """Record the rider assigned to this order.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        if self.status == STATUS_PENDING:
            self.status = STATUS_ASSIGNED

    def complete(self, tick):
        """Mark the order as delivered.

        Args:
            tick: Simulated tick of delivery.
        """
        self.status = STATUS_COMPLETED
        self.completed_tick = tick

    def time_taken(self):
        """Return the number of ticks from creation to delivery.

        Returns:
            Integer ticks, or None if the order is not completed.
        """
        if self.completed_tick is None:
            return None
        return self.completed_tick - self.start_tick

    def efficiency(self):
        """Return delivery efficiency as distance covered per tick.

        Returns:
            Float units per tick, or None if the order is not completed.
        """
        elapsed = self.time_taken()
        if elapsed is None:
            return None
        return self.distance / max(elapsed, 1)

    def to_dict(self):
        """Return a JSON-serialisable representation of the order.

        Returns:
            Dictionary of order fields.
        """
        return {
            "id": self.id,
            "status": self.status,
            "rider_id": self.rider_id,
            "restaurant": list(self.raw_restaurant),
            "customer": list(self.raw_customer),
            "restaurant_center": list(self.res_pos),
            "customer_center": list(self.cus_pos),
            "distance": self.distance,
            "start_tick": self.start_tick,
            "picked_up_tick": self.picked_up_tick,
            "completed_tick": self.completed_tick,
        }
