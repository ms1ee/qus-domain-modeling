"""Order data model: coordinates, lifecycle status and delivery metrics."""

import itertools
from typing import Any, Dict, Optional, Sequence

import globalvar
from path_planner import Point, manhattan, to_grid_point

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order number.
        res_pos: Restaurant grid point (cell centre).
        cus_pos: Customer grid point (cell centre).
        status: One of pending, assigned, picking_up, delivering, completed.
        rider_id: ID of the assigned rider, or None.
        start_time: Tick at which the order was created.
        pickup_time: Tick at which the rider reached the restaurant.
        complete_time: Tick at which the order was delivered.
        distance: Manhattan distance from restaurant to customer.
    """

    _id_sequence = itertools.count(1)

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from raw coordinates.

        Args:
            res_pos: ``(x, y)`` restaurant coordinates (0-800 expected).
            cus_pos: ``(x, y)`` customer coordinates (0-800 expected).

        Raises:
            ValueError: If either position is not an ``(x, y)`` pair.
        """
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("Order positions must be (x, y) pairs")
        self.id: int = next(Order._id_sequence)
        self.res_pos: Point = to_grid_point(res_pos[0], res_pos[1])
        self.cus_pos: Point = to_grid_point(cus_pos[0], cus_pos[1])
        self.status: str = STATUS_PENDING
        self.rider_id: Optional[int] = None
        self.start_time: int = int(globalvar.get_value("tick", 0))
        self.pickup_time: Optional[int] = None
        self.complete_time: Optional[int] = None
        self.distance: int = manhattan(self.res_pos, self.cus_pos)

    def assign_to(self, rider_id: int) -> None:
        """Record the rider this order is assigned to.

        The caller appends the order to ``rider.orders``.

        Args:
            rider_id: ID of the chosen rider.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_picking_up(self) -> None:
        """Mark that the rider has accepted the order and is heading to the restaurant."""
        self.status = STATUS_PICKING_UP

    def mark_delivering(self, tick: int) -> None:
        """Mark pickup completion and the start of delivery.

        Args:
            tick: Current simulation tick.
        """
        self.pickup_time = tick
        self.status = STATUS_DELIVERING

    def mark_completed(self, tick: int) -> None:
        """Mark the order as delivered.

        Args:
            tick: Current simulation tick.
        """
        self.complete_time = tick
        self.status = STATUS_COMPLETED

    @property
    def time_taken(self) -> Optional[int]:
        """Ticks from order creation to delivery, or None if not completed."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.start_time

    @property
    def efficiency(self) -> Optional[float]:
        """Delivery efficiency in distance units per tick, or None if unavailable."""
        taken = self.time_taken
        if not taken:
            return None
        return self.distance / taken

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self) -> str:
        return f"Order(id={self.id}, status={self.status}, rider_id={self.rider_id})"
