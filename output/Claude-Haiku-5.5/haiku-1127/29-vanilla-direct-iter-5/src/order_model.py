"""Order data model: coordinate conversion, lifecycle and efficiency data."""

from __future__ import annotations

import itertools
import math
from typing import Any, Dict, Optional, Sequence

from path_planner import PathPlanner


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        raw_res_pos, raw_cus_pos: Coordinates exactly as entered by the user.
        res_pos, cus_pos: Grid cell centres used for routing.
        status: ``pending`` -> ``assigned`` -> ``picking_up`` ->
            ``delivering`` -> ``completed``.
        rider_id: Identifier of the assigned rider (or None).
        start_tick, pickup_tick, end_tick: Lifecycle timestamps.
        distance: Straight-line distance between the two cell centres.
    """

    _id_sequence = itertools.count(1)

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int],
                 start_tick: int = 0) -> None:
        """Create an order and convert its coordinates to grid centres.

        Args:
            res_pos: ``(restaurant_x, restaurant_y)`` in range 0-800.
            cus_pos: ``(customer_x, customer_y)`` in range 0-800.
            start_tick: Simulation tick at creation.
        """
        self.id: int = next(Order._id_sequence)
        self.raw_res_pos = (int(res_pos[0]), int(res_pos[1]))
        self.raw_cus_pos = (int(cus_pos[0]), int(cus_pos[1]))
        self.res_pos = PathPlanner.cell_center(*self.raw_res_pos)
        self.cus_pos = PathPlanner.cell_center(*self.raw_cus_pos)
        self.distance = round(math.hypot(self.cus_pos[0] - self.res_pos[0],
                                         self.cus_pos[1] - self.res_pos[1]), 1)
        self.status: str = "pending"
        self.rider_id: Optional[int] = None
        self.start_tick: int = int(start_tick)
        self.pickup_tick: Optional[int] = None
        self.end_tick: Optional[int] = None

    def assign_to(self, rider_id: int) -> None:
        """Record the assigned rider and mark the order as assigned.

        The caller is responsible for appending the order to ``rider.orders``.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = int(rider_id)
        self.status = "assigned"

    def mark_picked_up(self, tick: int) -> None:
        """Record arrival at the restaurant.

        Args:
            tick: Simulation tick of the pickup.
        """
        self.pickup_tick = int(tick)
        self.status = "delivering"

    def complete(self, tick: int) -> None:
        """Mark the order as delivered.

        Args:
            tick: Simulation tick of the delivery.
        """
        self.end_tick = int(tick)
        self.status = "completed"

    @property
    def duration(self) -> Optional[int]:
        """Ticks from creation to completion, or None if not completed."""
        if self.end_tick is None:
            return None
        return self.end_tick - self.start_tick

    @property
    def efficiency(self) -> Optional[float]:
        """Delivery efficiency as distance units per tick, or None."""
        duration = self.duration
        if duration is None:
            return None
        return round(self.distance / max(duration, 1), 2)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "raw_restaurant": list(self.raw_res_pos),
            "raw_customer": list(self.raw_cus_pos),
            "restaurant_center": list(self.res_pos),
            "customer_center": list(self.cus_pos),
            "distance": self.distance,
            "status": self.status,
            "rider_id": self.rider_id,
            "start_tick": self.start_tick,
            "pickup_tick": self.pickup_tick,
            "end_tick": self.end_tick,
            "duration": self.duration,
            "efficiency": self.efficiency,
        }
