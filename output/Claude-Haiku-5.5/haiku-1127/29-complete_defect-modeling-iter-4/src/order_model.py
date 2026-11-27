"""Order data model: coordinates, lifecycle status and delivery metrics."""

import itertools
from typing import Any, Dict, Tuple

from globalvar import get_value
from grid import MAP_SIZE, snap_to_center

Point = Tuple[int, int]

_order_ids = itertools.count(1)


def _validate_point(point: Any, label: str) -> Point:
    """Validate an ``[x, y]`` pair of integers within the map range.

    Args:
        point: Two-element sequence of integers.
        label: Human-readable name used in error messages.

    Returns:
        The validated (x, y) tuple.

    Raises:
        ValueError: If the input is malformed or out of range.
    """
    try:
        x, y = point
    except (TypeError, ValueError):
        raise ValueError(f"{label} location must be an [x, y] pair") from None
    for name, value in (("x", x), ("y", y)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} {name} must be an integer")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(
                f"{label} {name} must be between 0 and {MAP_SIZE}, got {value}")
    return x, y


class Order:
    """A food delivery order from a restaurant to a customer.

    Input coordinates are validated and automatically converted to the centres
    of their grid cells.

    Attributes:
        id: Unique order identifier.
        restaurant_x, restaurant_y: Pickup cell-centre coordinates.
        customer_x, customer_y: Delivery cell-centre coordinates.
        start_time: Simulated tick at which the order was placed.
        completion_time: Tick at which delivery finished (None until done).
        picked_up_time: Tick at which the food was collected.
        distance: Total planned travel distance in units.
        time_taken: Ticks between placement and completion.
        status: One of created, queued, assigned, picking_up, delivering,
            completed.
        rider_id: ID of the assigned rider, or None.
    """

    def __init__(self, res_pos: Any, cus_pos: Any) -> None:
        """Create an order from restaurant and customer locations.

        Args:
            res_pos: ``[x, y]`` restaurant location (0-800).
            cus_pos: ``[x, y]`` customer location (0-800).

        Raises:
            ValueError: If a location is malformed or out of range.
        """
        res_x, res_y = _validate_point(res_pos, "restaurant")
        cus_x, cus_y = _validate_point(cus_pos, "customer")
        self.id: int = next(_order_ids)
        self.restaurant_x = snap_to_center(res_x)
        self.restaurant_y = snap_to_center(res_y)
        self.customer_x = snap_to_center(cus_x)
        self.customer_y = snap_to_center(cus_y)
        self.start_time: int = int(get_value("simulated_time", 0) or 0)
        self.completion_time = None
        self.picked_up_time = None
        self.distance: int = 0
        self.time_taken = None
        self.status: str = "created"
        self.rider_id = None

    @property
    def restaurant_pos(self) -> Point:
        """Restaurant cell-centre coordinates as a tuple."""
        return (self.restaurant_x, self.restaurant_y)

    @property
    def customer_pos(self) -> Point:
        """Customer cell-centre coordinates as a tuple."""
        return (self.customer_x, self.customer_y)

    def assign_to(self, rider_id: int) -> None:
        """Record the rider this order is assigned to.

        Args:
            rider_id: Identifier of the rider.
        """
        self.rider_id = rider_id
        self.status = "assigned"

    def mark_picked_up(self, time: int) -> None:
        """Mark the food as collected at the restaurant.

        Args:
            time: Simulated tick of the pickup.
        """
        self.picked_up_time = time
        self.status = "delivering"

    def add_distance(self, units: int) -> None:
        """Add planned travel distance to the order.

        Args:
            units: Distance in map units.
        """
        self.distance += int(units)

    def complete(self, time: int) -> None:
        """Mark the order as delivered and compute efficiency metrics.

        Args:
            time: Simulated tick of delivery.
        """
        self.completion_time = time
        self.time_taken = time - self.start_time
        self.status = "completed"

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
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

    def __repr__(self) -> str:
        return (f"Order(id={self.id}, status={self.status}, "
                f"restaurant={self.restaurant_pos}, customer={self.customer_pos})")
