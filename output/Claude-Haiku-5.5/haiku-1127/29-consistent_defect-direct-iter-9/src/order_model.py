"""Order data model: coordinates, lifecycle, and delivery statistics."""

import logging

import globalvar
from path_planner import MAP_SIZE, manhattan, snap_to_cell

logger = logging.getLogger("dispatch.order")

COMPLETED = "completed"


def _now():
    """Return the current simulation tick."""
    return globalvar.get_value("time", 0) or 0


def _validate_point(point):
    """Validate an ``(x, y)`` input pair.

    Raises:
        ValueError: If the point is malformed, non-integer or out of range.
    """
    try:
        x, y = point
    except (TypeError, ValueError):
        raise ValueError(f"Location must be an (x, y) pair, got {point!r}")
    for value in (x, y):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Coordinates must be integers, got {value!r}")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"Coordinate {value} out of range 0-{MAP_SIZE}")
    return int(x), int(y)


def _find_rider(rider_id):
    """Return the rider with ``rider_id`` from the global roster, or None."""
    for rider in globalvar.get_value("riders") or []:
        if rider.rider_id == rider_id:
            return rider
    return None


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order number.
        restaurant: Snapped ``(x, y)`` restaurant location.
        customer: Snapped ``(x, y)`` customer location.
        status: "pending", "assigned", "picking_up", "delivering" or "completed".
        rider_id: Id of the assigned rider, or None.
        start_time: Tick at which the order was created.
        pickup_time: Tick at which the rider reached the restaurant.
        complete_time: Tick at which the order was delivered.
        distance: Manhattan distance between restaurant and customer.
        time_taken: Ticks between creation and completion.
        efficiency: Distance covered per tick of total time taken.
    """

    _id_counter = 0

    def __init__(self, res_pos, cus_pos):
        """Create an order from raw restaurant and customer coordinates.

        Args:
            res_pos: ``(x, y)`` restaurant coordinates in the range 0-800.
            cus_pos: ``(x, y)`` customer coordinates in the range 0-800.

        Raises:
            ValueError: If coordinates are malformed or out of range.
        """
        restaurant = _validate_point(res_pos)
        customer = _validate_point(cus_pos)
        Order._id_counter += 1
        self.id = Order._id_counter
        self.restaurant = snap_to_cell(*restaurant)
        self.customer = snap_to_cell(*customer)
        self.status = "pending"
        self.rider_id = None
        self.start_time = _now()
        self.pickup_time = None
        self.complete_time = None
        self.distance = manhattan(self.restaurant, self.customer)
        self.time_taken = None
        self.efficiency = None

    def assign_to(self, rider_id):
        """Assign this order to the rider with ``rider_id``.

        The order is appended to ``rider.orders`` and the rider is notified.

        Args:
            rider_id: Identifier of the target rider.

        Raises:
            ValueError: If the rider does not exist or the order is completed.
        """
        if self.status == COMPLETED:
            raise ValueError(f"Order #{self.id} is already completed")
        rider = _find_rider(rider_id)
        if rider is None:
            raise ValueError(f"Rider #{rider_id} does not exist")
        self.rider_id = rider_id
        self.status = "assigned"
        rider.orders.append(self)
        rider.accept_order(self)
        logger.info("Order #%s assigned to rider #%s", self.id, rider_id)

    def complete(self, time_now):
        """Mark the order as delivered and record timing statistics.

        Args:
            time_now: Tick at which delivery happened.
        """
        self.status = COMPLETED
        self.complete_time = time_now
        self.time_taken = max(0, time_now - self.start_time)
        self.efficiency = round(self.distance / max(self.time_taken, 1), 2)

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.restaurant),
            "customer": list(self.customer),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
