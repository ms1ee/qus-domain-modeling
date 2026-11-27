"""Order data model.

An order is created from user input in the form
``[restaurant_x, restaurant_y, customer_x, customer_y]`` with coordinates in
the range 0-800. Coordinates are converted to grid cell centers.
"""

import itertools
import logging

from globalvar import get_value
from path_planner import PathPlanner, cell_center

logger = logging.getLogger(__name__)

COORD_MIN = 0
COORD_MAX = 800

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _current_tick() -> int:
    """Return the current simulated tick (0 if unavailable)."""
    value = get_value("tick")
    return value if isinstance(value, int) else 0


def _validate_point(point, label: str) -> tuple:
    """Validate a raw (x, y) input pair.

    Args:
        point: Sequence of two integers.
        label: Name used in error messages (e.g. "restaurant").

    Returns:
        A tuple (x, y) of validated integers.

    Raises:
        ValueError: If the point is malformed, not integer or out of range.
    """
    try:
        x, y = point
    except (TypeError, ValueError):
        raise ValueError(f"{label} location must contain exactly 2 values")
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} coordinates must be integers")
        if not COORD_MIN <= value <= COORD_MAX:
            raise ValueError(
                f"{label} coordinates must be in range {COORD_MIN}-{COORD_MAX}"
            )
    return int(x), int(y)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier (auto-incremented).
        res_input: Raw restaurant coordinates as entered by the user.
        cus_input: Raw customer coordinates as entered by the user.
        res_pos: Restaurant grid cell center (x, y).
        cus_pos: Customer grid cell center (x, y).
        status: One of "pending", "assigned", "picking_up", "delivering",
            "completed".
        rider_id: ID of the assigned rider, or None.
        start_tick: Tick at which the order was created.
        pickup_tick: Tick at which the rider reached the restaurant.
        completion_tick: Tick at which the order was delivered.
        distance: Route length from restaurant to customer in units.
    """

    _counter = itertools.count(1)

    def __init__(self, res_pos, cus_pos) -> None:
        """Create an order and convert coordinates to grid cell centers.

        Args:
            res_pos: Restaurant (x, y) in range 0-800.
            cus_pos: Customer (x, y) in range 0-800.

        Raises:
            ValueError: If coordinates are malformed, non-integer or out of
                range.
        """
        self.res_input = _validate_point(res_pos, "restaurant")
        self.cus_input = _validate_point(cus_pos, "customer")
        self.id = next(Order._counter)
        self.res_pos = (cell_center(self.res_input[0]), cell_center(self.res_input[1]))
        self.cus_pos = (cell_center(self.cus_input[0]), cell_center(self.cus_input[1]))
        self.status = STATUS_PENDING
        self.rider_id = None
        self.start_tick = _current_tick()
        self.pickup_tick = None
        self.completion_tick = None
        planner = PathPlanner()
        self.distance = planner.route_length(planner.route(self.res_pos, self.cus_pos))
        logger.info(
            "Order %d created: restaurant=%s customer=%s",
            self.id,
            self.res_pos,
            self.cus_pos,
        )

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_picked_up(self, tick: int) -> None:
        """Record arrival at the restaurant and switch to delivering.

        Args:
            tick: Current simulated tick.
        """
        self.pickup_tick = tick
        self.status = STATUS_DELIVERING

    def complete(self, tick: int) -> None:
        """Mark the order as delivered.

        Args:
            tick: Current simulated tick.
        """
        self.completion_tick = tick
        self.status = STATUS_COMPLETED
        logger.info("Order %d completed at tick %d", self.id, tick)

    @property
    def time_taken(self):
        """Ticks from creation to completion, or None if not completed."""
        if self.completion_tick is None:
            return None
        return self.completion_tick - self.start_tick

    @property
    def efficiency(self):
        """Delivery efficiency in units per tick, or None if not completed.

        Returns None when the order is incomplete or completed in zero ticks.
        """
        taken = self.time_taken
        if not taken:
            return None
        return self.distance / taken

    def __repr__(self) -> str:
        return f"Order(id={self.id}, status={self.status}, rider={self.rider_id})"
