"""Order data model.

An order is created from a restaurant position and a customer position, both
given as ``[x, y]`` integer pairs in the range 0-800 (or as Location objects).
Each order is served by one rider through the pickup -> delivery lifecycle.
"""

import itertools
from typing import Any, Dict, Optional, Sequence, Union

from globalvar import get_value
from location import Location

_ORDER_IDS = itertools.count(1)

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"

PositionInput = Union[Location, Sequence[int]]


def _to_location(value: PositionInput) -> Location:
    """Convert an ``[x, y]`` pair or Location into a validated Location.

    Raises:
        ValueError: If the value is malformed or out of range.
    """
    if isinstance(value, Location):
        return value
    try:
        x, y = value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"position must be [x, y], got {value!r}") from exc
    return Location.from_xy(x, y)


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order number.
        res_pos: Restaurant (pickup) Location.
        cus_pos: Customer (delivery) Location.
        status: One of pending, assigned, picking_up, delivering, completed.
        rider_id: ID of the assigned rider, or None.
        start_time: Simulated tick when the order was created.
        pickup_time: Tick when the food was collected, or None.
        completion_time: Tick when the order was delivered, or None.
        distance: Planned rider distance (rider -> restaurant -> customer).
        time_taken: Ticks from creation to delivery, or None.
    """

    def __init__(self, res_pos: PositionInput, cus_pos: PositionInput,
                 start_time: Optional[int] = None) -> None:
        """Create a pending order.

        Args:
            res_pos: Restaurant position as ``[x, y]`` or Location.
            cus_pos: Customer position as ``[x, y]`` or Location.
            start_time: Creation tick. Defaults to the current simulated time.

        Raises:
            ValueError: If either position is invalid.
        """
        self.id = next(_ORDER_IDS)
        self.res_pos = _to_location(res_pos)
        self.cus_pos = _to_location(cus_pos)
        self.status = STATUS_PENDING
        self.rider_id: Optional[int] = None
        if start_time is None:
            start_time = get_value("simulated_time") or 0
        self.start_time = start_time
        self.pickup_time: Optional[int] = None
        self.completion_time: Optional[int] = None
        self.distance = 0
        self.time_taken: Optional[int] = None

    @property
    def res_node(self) -> tuple:
        """Restaurant grid node as ``(col, row)``."""
        return self.res_pos.node

    @property
    def cus_node(self) -> tuple:
        """Customer grid node as ``(col, row)``."""
        return self.cus_pos.node

    def assign_to(self, rider_id: int) -> None:
        """Record the assigned rider and mark the order as assigned."""
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_accepted(self) -> None:
        """Mark that the rider has started heading to the restaurant."""
        self.status = STATUS_PICKING_UP

    def mark_picked_up(self, time: int) -> None:
        """Mark that the food has been collected at tick ``time``."""
        self.pickup_time = time
        self.status = STATUS_DELIVERING

    def complete(self, time: int) -> None:
        """Mark the order delivered at tick ``time`` and compute the time taken."""
        self.completion_time = time
        self.time_taken = time - self.start_time
        self.status = STATUS_COMPLETED

    @property
    def is_finished(self) -> bool:
        """True once the order has been delivered."""
        return self.status == STATUS_COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of this order."""
        return {
            "id": self.id,
            "status": self.status,
            "rider_id": self.rider_id,
            "restaurant": [self.res_pos.x, self.res_pos.y],
            "customer": [self.cus_pos.x, self.cus_pos.y],
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
