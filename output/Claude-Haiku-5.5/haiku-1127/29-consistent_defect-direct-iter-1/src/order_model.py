"""Order data model."""

from typing import Any, Dict, Optional, Sequence

import globalvar
from path_planner import PathPlanner

ORDER_PENDING = "pending"
ORDER_ASSIGNED = "assigned"
ORDER_PICKED_UP = "picked_up"
ORDER_COMPLETED = "completed"


def _next_order_id() -> int:
    """Return a new unique order ID and store the counter globally."""
    counter = int(globalvar.get_value("order_id_counter", 0) or 0) + 1
    globalvar.set_value("order_id_counter", counter)
    return counter


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant grid point ``(x, y)`` (top-left of its cell).
        cus_pos: Customer grid point ``(x, y)`` (top-left of its cell).
        status: One of "pending", "assigned", "picked_up", "completed".
        rider_id: ID of the assigned rider, or None.
        start_time: Tick at which the order was created.
        assigned_time: Tick at which the order was assigned.
        pickup_time: Tick at which the rider collected the food.
        completion_time: Tick at which the order was delivered.
        distance: Street distance between restaurant and customer.
        time_taken: Ticks from creation to delivery, once completed.
        efficiency: Distance per tick (delivery efficiency), once completed.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and snap its coordinates to grid points.

        Args:
            res_pos: Raw restaurant coordinates ``(x, y)``.
            cus_pos: Raw customer coordinates ``(x, y)``.
        """
        self.id = _next_order_id()
        self.res_pos = PathPlanner.snap_point(res_pos[0], res_pos[1])
        self.cus_pos = PathPlanner.snap_point(cus_pos[0], cus_pos[1])
        self.status = ORDER_PENDING
        self.rider_id: Optional[int] = None
        self.start_time = globalvar.current_tick()
        self.assigned_time: Optional[int] = None
        self.pickup_time: Optional[int] = None
        self.completion_time: Optional[int] = None
        self.distance = PathPlanner.manhattan(self.res_pos, self.cus_pos)
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to a rider.

        Args:
            rider_id: ID of the rider receiving the order.

        Raises:
            ValueError: If the order is not pending.
        """
        if self.status != ORDER_PENDING:
            raise ValueError(
                f"Order #{self.id} cannot be assigned from status '{self.status}'."
            )
        self.rider_id = rider_id
        self.status = ORDER_ASSIGNED
        self.assigned_time = globalvar.current_tick()

    def mark_picked_up(self, tick: Optional[int] = None) -> None:
        """Record that the rider collected the food at the restaurant.

        Args:
            tick: Tick of the pickup; defaults to the current tick.

        Raises:
            ValueError: If the order is not in the assigned state.
        """
        if self.status != ORDER_ASSIGNED:
            raise ValueError(
                f"Order #{self.id} cannot be picked up from status '{self.status}'."
            )
        self.status = ORDER_PICKED_UP
        self.pickup_time = globalvar.current_tick() if tick is None else tick

    def complete(self, tick: Optional[int] = None) -> None:
        """Mark the order as delivered and compute delivery statistics.

        Args:
            tick: Tick of the delivery; defaults to the current tick.

        Raises:
            ValueError: If the order has not been picked up.
        """
        if self.status != ORDER_PICKED_UP:
            raise ValueError(
                f"Order #{self.id} cannot be completed from status '{self.status}'."
            )
        end = globalvar.current_tick() if tick is None else tick
        self.status = ORDER_COMPLETED
        self.completion_time = end
        self.time_taken = end - self.start_time
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 2)
        else:
            self.efficiency = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "assigned_time": self.assigned_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
