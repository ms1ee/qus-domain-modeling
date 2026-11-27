"""Order data model for the food delivery simulator."""

import itertools
from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from path_planner import snap_to_cell

STATUS_CREATED = "created"
STATUS_ASSIGNED = "assigned"
STATUS_PICKED_UP = "picked_up"
STATUS_COMPLETED = "completed"
ACTIVE_STATUSES = (STATUS_ASSIGNED, STATUS_PICKED_UP)

_order_ids = itertools.count(1)


class Order:
    """A food delivery order from a restaurant to a customer.

    Coordinates supplied by the user are snapped to the top-left corner of
    their grid cell, so restaurant and customer locations always lie on
    street intersections.

    Attributes:
        id: Unique, auto-incremented order identifier.
        restaurant_x: Snapped restaurant x coordinate.
        restaurant_y: Snapped restaurant y coordinate.
        customer_x: Snapped customer x coordinate.
        customer_y: Snapped customer y coordinate.
        status: One of "created", "assigned", "picked_up", "completed".
        rider_id: Identifier of the assigned rider, or None.
        start_time: Tick at which the order was created.
        completion_time: Tick at which the order was delivered, or None.
        distance: Manhattan distance from restaurant to customer.
        time_taken: Ticks from creation to delivery, or None.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from raw coordinates.

        Args:
            res_pos: Restaurant coordinates ``[x, y]`` in the range 0-800.
            cus_pos: Customer coordinates ``[x, y]`` in the range 0-800.
        """
        rx, ry = int(res_pos[0]), int(res_pos[1])
        cx, cy = int(cus_pos[0]), int(cus_pos[1])
        self.id: int = next(_order_ids)
        self.restaurant_x: int = snap_to_cell(rx)
        self.restaurant_y: int = snap_to_cell(ry)
        self.customer_x: int = snap_to_cell(cx)
        self.customer_y: int = snap_to_cell(cy)
        self.status: str = STATUS_CREATED
        self.rider_id: Optional[int] = None
        self.start_time: int = int(globalvar.get_value("current_tick", 0) or 0)
        self.completion_time: Optional[int] = None
        self.distance: float = float(
            abs(self.customer_x - self.restaurant_x)
            + abs(self.customer_y - self.restaurant_y)
        )
        self.time_taken: Optional[int] = None

    @property
    def restaurant_pos(self) -> Tuple[int, int]:
        """Restaurant grid point as a tuple."""
        return (self.restaurant_x, self.restaurant_y)

    @property
    def customer_pos(self) -> Tuple[int, int]:
        """Customer grid point as a tuple."""
        return (self.customer_x, self.customer_y)

    @property
    def is_active(self) -> bool:
        """True while the order is assigned and not yet delivered."""
        return self.status in ACTIVE_STATUSES

    @property
    def efficiency(self) -> Optional[float]:
        """Delivery efficiency expressed as distance covered per tick."""
        if self.time_taken is None:
            return None
        return self.distance / max(self.time_taken, 1)

    def assign_to(self, rider_id: int) -> None:
        """Bind the order to a rider and mark it as assigned.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_picked_up(self) -> None:
        """Mark the order as picked up at the restaurant."""
        self.status = STATUS_PICKED_UP

    def mark_completed(self, now: int) -> None:
        """Mark the order as delivered and record efficiency data.

        Args:
            now: Tick at which delivery happened.
        """
        self.status = STATUS_COMPLETED
        self.completion_time = now
        self.time_taken = max(0, now - self.start_time)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the order."""
        return {
            "id": self.id,
            "restaurant": [self.restaurant_x, self.restaurant_y],
            "customer": [self.customer_x, self.customer_y],
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
