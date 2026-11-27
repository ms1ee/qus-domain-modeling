"""Order data model.

An order is created from user coordinates ``[restaurant_x, restaurant_y,
customer_x, customer_y]``, snapped to the street grid, assigned to a rider,
and finally marked completed when the rider delivers it.
"""

import itertools
import logging
from typing import Any, Dict, Optional, Sequence

import globalvar
from path_planner import PathPlanner, Point

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"

# Income credited to system funds for each delivered order.
ORDER_FEE = 300


def _current_tick() -> int:
    """Return the current simulated tick from the global store."""
    return int(globalvar.get_value("tick", 0) or 0)


class Order:
    """A single food delivery order.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant location (snapped to a street intersection).
        cus_pos: Customer location (snapped to a street intersection).
        status: One of "pending", "assigned", "completed", "cancelled".
        rider_id: ID of the assigned rider, or None.
        start_tick: Tick at which the order was created.
        accepted_tick: Tick at which the order was assigned to a rider.
        completed_tick: Tick at which the order was delivered.
        distance: Planned route length from restaurant to customer (units).
        time_taken: Ticks between creation and delivery.
        efficiency: Distance covered per tick (distance / time_taken).
    """

    _id_source = itertools.count(1)

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: ``(x, y)`` of the restaurant, range 0-800.
            cus_pos: ``(x, y)`` of the customer, range 0-800.
        """
        self.id = next(Order._id_source)
        self.res_pos: Point = self._normalize(res_pos)
        self.cus_pos: Point = self._normalize(cus_pos)
        self.status = STATUS_PENDING
        self.rider_id: Optional[int] = None
        self.start_tick = _current_tick()
        self.accepted_tick: Optional[int] = None
        self.completed_tick: Optional[int] = None
        self.distance = PathPlanner.route_length(
            [self.res_pos] + PathPlanner.plan(self.res_pos, self.cus_pos)
        )
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None
        logger.debug(
            "Order %d created: restaurant=%s customer=%s distance=%d",
            self.id,
            self.res_pos,
            self.cus_pos,
            self.distance,
        )

    @staticmethod
    def _normalize(pos: Sequence[int]) -> Point:
        """Snap a raw ``(x, y)`` pair to the nearest street intersection."""
        x, y = pos
        return (PathPlanner.snap_to_road(int(x)), PathPlanner.snap_to_road(int(y)))

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to the rider with ``rider_id``."""
        self.rider_id = int(rider_id)
        self.status = STATUS_ASSIGNED
        self.accepted_tick = _current_tick()

    def mark_completed(self, tick: Optional[int] = None) -> None:
        """Mark the order as delivered and record delivery efficiency.

        Args:
            tick: Completion tick. Defaults to the current simulated tick.
        """
        completed = _current_tick() if tick is None else int(tick)
        self.completed_tick = completed
        self.status = STATUS_COMPLETED
        self.time_taken = max(0, completed - self.start_tick)
        self.efficiency = round(self.distance / max(1, self.time_taken), 2)
        logger.info(
            "Order %d completed at tick %d (time=%d, efficiency=%.2f)",
            self.id,
            completed,
            self.time_taken,
            self.efficiency,
        )

    def cancel(self) -> None:
        """Mark the order as cancelled (no rider could be assigned)."""
        self.status = STATUS_CANCELLED
        logger.warning("Order %d cancelled", self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_tick": self.start_tick,
            "accepted_tick": self.accepted_tick,
            "completed_tick": self.completed_tick,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
