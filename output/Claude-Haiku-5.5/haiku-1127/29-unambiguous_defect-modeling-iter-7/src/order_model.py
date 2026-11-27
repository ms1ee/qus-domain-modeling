"""Order data model for the dispatch system."""

import itertools
from typing import Sequence, Tuple

from grid import Grid

ORDER_STATUSES = ("pending", "assigned", "picking_up", "delivering", "completed")

_ORDER_ID_SEQUENCE = itertools.count(1)
_GRID = Grid()


def _validated_point(point: Sequence[int], label: str) -> Tuple[int, int]:
    """Validate a user supplied (x, y) pair.

    Args:
        point: Two-element sequence of integers.
        label: Human readable name used in error messages.

    Returns:
        Tuple[int, int]: The validated coordinates.

    Raises:
        ValueError: If the pair is malformed, non-integer or out of range.
    """
    if len(point) != 2:
        raise ValueError(f"{label} location must have exactly two coordinates")
    x, y = point
    if not (isinstance(x, int) and isinstance(y, int)) or isinstance(x, bool) or isinstance(y, bool):
        raise ValueError(f"{label} coordinates must be integers")
    if not _GRID.is_valid_coord(x, y):
        raise ValueError(
            f"{label} coordinates must be within 0-{_GRID.map_size}, got ({x}, {y})"
        )
    return x, y


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant location snapped to the grid, (x, y).
        cus_pos: Customer location snapped to the grid, (x, y).
        status: One of ``ORDER_STATUSES``; ``"completed"`` after delivery.
        rider_id: Identifier of the assigned rider, or None.
        start_time: Tick at which the order was created.
        completion_time: Tick at which the order was delivered, or None.
        distance: Manhattan distance between restaurant and customer.
        time_taken: Ticks from creation to delivery, or None.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int], start_time: int = 0):
        """Create an order and transform its coordinates to grid locations.

        Args:
            res_pos: Restaurant coordinates (x, y), range 0-800.
            cus_pos: Customer coordinates (x, y), range 0-800.
            start_time: Tick at which the order is created.

        Raises:
            ValueError: If coordinates are malformed or out of range.
        """
        rx, ry = _validated_point(res_pos, "restaurant")
        cx, cy = _validated_point(cus_pos, "customer")
        self.id = next(_ORDER_ID_SEQUENCE)
        self.res_pos = _GRID.snap_to_location(rx, ry)
        self.cus_pos = _GRID.snap_to_location(cx, cy)
        self.restaurant_x, self.restaurant_y = self.res_pos
        self.customer_x, self.customer_y = self.cus_pos
        self.status = "pending"
        self.rider_id = None
        self.start_time = int(start_time)
        self.completion_time = None
        self.distance = abs(self.restaurant_x - self.customer_x) + abs(
            self.restaurant_y - self.customer_y
        )
        self.time_taken = None

    @classmethod
    def from_sequence(cls, values: Sequence[int], start_time: int = 0) -> "Order":
        """Create an order from the ``[restaurant_x, restaurant_y, customer_x, customer_y]`` format.

        Args:
            values: Four integers.
            start_time: Tick at which the order is created.

        Returns:
            Order: The new order.

        Raises:
            ValueError: If the sequence does not contain exactly four values.
        """
        if len(values) != 4:
            raise ValueError("order requires four coordinates")
        return cls(values[0:2], values[2:4], start_time)

    def assign_to(self, rider_id: int) -> None:
        """Record assignment to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.

        Returns:
            None
        """
        self.rider_id = rider_id
        self.status = "assigned"

    def mark_picking_up(self) -> None:
        """Mark that the rider is heading to the restaurant.

        Returns:
            None
        """
        self.status = "picking_up"

    def mark_delivering(self) -> None:
        """Mark that the rider has picked up and is heading to the customer.

        Returns:
            None
        """
        self.status = "delivering"

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and record efficiency data.

        Args:
            tick: Simulation tick at which delivery happened.

        Returns:
            None
        """
        self.status = "completed"
        self.completion_time = int(tick)
        self.time_taken = self.completion_time - self.start_time

    def is_completed(self) -> bool:
        """Return True if the order has been delivered.

        Returns:
            bool: Completion flag.
        """
        return self.status == "completed"

    def to_dict(self) -> dict:
        """Serialize the order to a JSON-compatible dictionary.

        Returns:
            dict: Order attributes.
        """
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
