"""Order data model.

An order holds the restaurant (pickup) and customer (drop-off) positions as
entered by the user, plus their grid cell center points used for routing.
"""

import itertools
from typing import Any, Dict, Optional, Sequence, Tuple

from pathplanner import to_cell_center, validate_coordinate

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"

_ORDER_IDS = itertools.count(1)


def _parse_point(pos: Sequence[int]) -> Tuple[int, int]:
    """Validate an ``(x, y)`` position.

    Args:
        pos: Position as a 2-element list or tuple.

    Returns:
        Validated tuple ``(x, y)``.

    Raises:
        ValueError: If the shape or the coordinate values are invalid.
    """
    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
        raise ValueError("position must contain exactly two values (x, y)")
    return validate_coordinate(pos[0]), validate_coordinate(pos[1])


class Order:
    """A food delivery order with pickup and drop-off locations."""

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order.

        Args:
            res_pos: Restaurant position ``(x, y)`` in range 0-800.
            cus_pos: Customer position ``(x, y)`` in range 0-800.

        Raises:
            ValueError: If a position is malformed or out of range.
        """
        self.id: int = next(_ORDER_IDS)
        self.res_pos: Tuple[int, int] = _parse_point(res_pos)
        self.cus_pos: Tuple[int, int] = _parse_point(cus_pos)
        self.res_center: Tuple[int, int] = to_cell_center(*self.res_pos)
        self.cus_center: Tuple[int, int] = to_cell_center(*self.cus_pos)
        self.status: str = STATUS_PENDING
        self.rider_id: Optional[int] = None
        self.start_tick: int = 0
        self.finish_tick: Optional[int] = None
        self.distance: int = 0

    def assign_to(self, rider_id: int) -> None:
        """Record the rider this order is assigned to.

        Args:
            rider_id: Identifier of the assigned rider.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def set_status(self, status: str) -> None:
        """Update the lifecycle status of the order.

        Args:
            status: One of the STATUS_* constants.
        """
        self.status = status

    def complete(self, tick: int) -> None:
        """Mark the order as delivered.

        Args:
            tick: Simulated time at which delivery finished.
        """
        self.status = STATUS_COMPLETED
        self.finish_tick = tick

    @property
    def time_taken(self) -> Optional[int]:
        """Return the number of ticks from creation to completion, if finished."""
        if self.finish_tick is None:
            return None
        return self.finish_tick - self.start_tick

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order.

        Returns:
            Dictionary describing the order.
        """
        return {
            "id": self.id,
            "status": self.status,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "rider_id": self.rider_id,
            "start_tick": self.start_tick,
            "finish_tick": self.finish_tick,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self) -> str:
        return f"Order(id={self.id}, status={self.status!r}, rider={self.rider_id})"
