"""Order data model for the food delivery dispatch system.

An order is described by ``[restaurant_x, restaurant_y, customer_x, customer_y]``.
Coordinates are snapped to the nearest location on the street grid.
"""

from typing import Any, Dict, List, Optional, Sequence

from globalvar import get_value, next_id
from path_planner import PathPlanner, Point, snap_point

STATUS_CREATED = "created"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


class Order:
    """A single food delivery order.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant location ``(x, y)``.
        cus_pos: Customer location ``(x, y)``.
        status: One of the ``STATUS_*`` constants. ``"completed"`` after delivery.
        rider_id: ID of the assigned rider, or None.
        start_time: Tick when the order was created.
        assigned_time: Tick when the order was assigned to a rider.
        completed_time: Tick when the order was delivered.
        distance: Street distance from restaurant to customer, in units.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and compute its delivery distance.

        Args:
            res_pos: Restaurant coordinates ``(x, y)``; snapped to the grid.
            cus_pos: Customer coordinates ``(x, y)``; snapped to the grid.
        """
        self.id: int = next_id("order_id_counter")
        self.res_pos: Point = snap_point(res_pos[0], res_pos[1])
        self.cus_pos: Point = snap_point(cus_pos[0], cus_pos[1])
        self.status: str = STATUS_CREATED
        self.rider_id: Optional[int] = None
        self.start_time: int = int(get_value("tick", 0))
        self.assigned_time: Optional[int] = None
        self.completed_time: Optional[int] = None
        route = PathPlanner().find_path(self.res_pos, self.cus_pos)
        self.distance: int = len(route) if route is not None else 0

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to a rider.

        Args:
            rider_id: ID of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED
        self.assigned_time = int(get_value("tick", 0))

    def complete(self, tick: int) -> None:
        """Mark the order as delivered.

        Args:
            tick: Simulation tick at which delivery happened.
        """
        self.status = STATUS_COMPLETED
        self.completed_time = int(tick)

    @property
    def time_taken(self) -> Optional[int]:
        """Ticks from order creation to delivery, or None if not completed."""
        if self.completed_time is None:
            return None
        return self.completed_time - self.start_time

    def to_list(self) -> List[int]:
        """Return the order in the ``[rx, ry, cx, cy]`` format."""
        return [self.res_pos[0], self.res_pos[1], self.cus_pos[0], self.cus_pos[1]]

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "coordinates": self.to_list(),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "assigned_time": self.assigned_time,
            "completed_time": self.completed_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
