"""Order data model.

An order is created from user input ``[restaurant_x, restaurant_y,
customer_x, customer_y]``. Coordinates are snapped to grid cell corners and
the order carries its own lifecycle timing and efficiency data.
"""

from __future__ import annotations

import itertools
from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from path_planner import manhattan, snap_point

PENDING = "pending"
ASSIGNED = "assigned"
PICKING_UP = "picking_up"
DELIVERING = "delivering"
COMPLETED = "completed"

_ORDER_IDS = itertools.count(1)


def _current_tick() -> int:
    """Return the current simulation tick from the global store."""
    return int(globalvar.get_value("sim_time", 0) or 0)


class Order:
    """A food delivery order from restaurant to customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant grid corner ``(x, y)``.
        cus_pos: Customer grid corner ``(x, y)``.
        status: One of pending, assigned, picking_up, delivering, completed.
        rider_id: ID of the assigned rider, or None.
        start_time: Tick at which the order was created.
        accepted_time: Tick at which the rider started pickup.
        pickup_time: Tick at which the rider reached the restaurant.
        completion_time: Tick at which the order was delivered.
        distance: Manhattan distance restaurant to customer.
        time_taken: Ticks from creation to completion.
        efficiency: Distance per tick for the completed order.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and snap both locations to grid corners.

        Args:
            res_pos: Restaurant coordinates ``(x, y)``.
            cus_pos: Customer coordinates ``(x, y)``.
        """
        self.id: int = next(_ORDER_IDS)
        self.res_pos: Tuple[int, int] = snap_point(res_pos)
        self.cus_pos: Tuple[int, int] = snap_point(cus_pos)
        self.status: str = PENDING
        self.rider_id: Optional[int] = None
        self.start_time: int = _current_tick()
        self.accepted_time: Optional[int] = None
        self.pickup_time: Optional[int] = None
        self.completion_time: Optional[int] = None
        self.distance: int = manhattan(self.res_pos, self.cus_pos)
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None

    def assign_to(self, rider_id: int) -> None:
        """Record the rider this order has been assigned to.

        The caller is responsible for appending the order to ``rider.orders``.

        Args:
            rider_id: Identifier of the chosen rider.
        """
        self.rider_id = int(rider_id)
        self.status = ASSIGNED

    def mark_accepted(self, tick: int) -> None:
        """Mark that the rider has started the pickup trip."""
        self.status = PICKING_UP
        if self.accepted_time is None:
            self.accepted_time = tick

    def mark_picked_up(self, tick: int) -> None:
        """Mark that the rider has reached the restaurant."""
        self.status = DELIVERING
        self.pickup_time = tick

    def complete(self, tick: int) -> None:
        """Mark the order delivered and compute delivery efficiency.

        Args:
            tick: Simulation tick at which delivery happened.
        """
        self.status = COMPLETED
        self.completion_time = tick
        self.time_taken = max(0, tick - self.start_time)
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 3)
        else:
            self.efficiency = float(self.distance)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "accepted_time": self.accepted_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }

    def __repr__(self) -> str:
        return f"Order(id={self.id}, status={self.status!r}, rider_id={self.rider_id})"
