"""Order data model."""

import itertools
from typing import Any, Dict, Optional, Sequence

import globalvar
from path_planner import PathPlanner

_id_counter = itertools.count(1)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant grid point ``(x, y)`` (snapped to cell corners).
        cus_pos: Customer grid point ``(x, y)`` (snapped to cell corners).
        status: One of ``"created"``, ``"assigned"``, ``"picking_up"``,
            ``"delivering"``, ``"completed"``.
        rider_id: ID of the assigned rider, or None.
        start_time: Simulated tick when the order was created.
        complete_time: Simulated tick when delivery finished, or None.
        distance: Manhattan distance from restaurant to customer (units).
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and snap its coordinates to grid corners.

        Args:
            res_pos: Restaurant coordinates ``(x, y)``.
            cus_pos: Customer coordinates ``(x, y)``.
        """
        self.id: int = next(_id_counter)
        rx, ry = res_pos
        cx, cy = cus_pos
        self.res_pos: tuple = PathPlanner.snap_point(int(rx), int(ry))
        self.cus_pos: tuple = PathPlanner.snap_point(int(cx), int(cy))
        self.status: str = "created"
        self.rider_id: Optional[int] = None
        self.start_time: int = globalvar.get_value("time", 0)
        self.complete_time: Optional[int] = None
        self.distance: int = PathPlanner.manhattan(self.res_pos, self.cus_pos)

    def assign_to(self, rider_id: int) -> None:
        """Record the assigned rider and mark the order as assigned.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = int(rider_id)
        if self.status == "created":
            self.status = "assigned"

    def complete(self, time: int) -> None:
        """Mark the order as delivered.

        Args:
            time: Simulated tick of completion.
        """
        self.status = "completed"
        self.complete_time = time

    @property
    def time_taken(self) -> Optional[int]:
        """Ticks from creation to completion, or None if not completed."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.start_time

    @property
    def efficiency(self) -> Optional[float]:
        """Delivery efficiency: distance units per tick, or None."""
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
            "complete_time": self.complete_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }

    def __repr__(self) -> str:
        return f"Order(id={self.id}, status={self.status}, rider={self.rider_id})"
