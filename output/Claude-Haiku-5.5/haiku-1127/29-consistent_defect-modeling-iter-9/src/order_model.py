"""Order data model.

An order is created from restaurant and customer coordinates. Coordinates
are snapped to the top-left corner of their grid cell on creation.
"""

import itertools
import logging
from typing import List, Optional, Tuple

from globalvar import get_value
from grid_map import GridMap
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.order_model")

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"

_id_sequence = itertools.count(1)


class Order:
    """A food delivery order from a restaurant to a customer."""

    def __init__(self, res_pos, cus_pos) -> None:
        """Create an order and snap its coordinates to grid cells.

        Args:
            res_pos: Restaurant (x, y) in range 0-800.
            cus_pos: Customer (x, y) in range 0-800.
        """
        grid = GridMap()
        rx, ry = grid.snap(res_pos[0], res_pos[1])
        cx, cy = grid.snap(cus_pos[0], cus_pos[1])
        self.id: int = next(_id_sequence)
        self.restaurant_x: int = rx
        self.restaurant_y: int = ry
        self.customer_x: int = cx
        self.customer_y: int = cy
        self.status: str = STATUS_PENDING
        self.assigned_rider_id: Optional[int] = None
        self.start_time: int = int(get_value("current_tick") or 0)
        self.completion_time: Optional[int] = None
        self.time_taken: Optional[int] = None
        planner = PathPlanner(grid)
        route = planner.plan((rx, ry), (cx, cy))
        self.distance: float = float(planner.route_length((rx, ry), route))
        self.route: List[Tuple[int, int]] = []
        logger.debug("Created order %d: %s -> %s", self.id, self.restaurant_pos, self.customer_pos)

    @property
    def restaurant_pos(self) -> Tuple[int, int]:
        """Restaurant grid point as (x, y)."""
        return self.restaurant_x, self.restaurant_y

    @property
    def customer_pos(self) -> Tuple[int, int]:
        """Customer grid point as (x, y)."""
        return self.customer_x, self.customer_y

    def is_completed(self) -> bool:
        """Return True once the order has been delivered."""
        return self.status == STATUS_COMPLETED

    def assign_to(self, rider_id: int) -> None:
        """Record the rider that serves this order.

        Args:
            rider_id: Identifier of the assigned rider.
        """
        self.assigned_rider_id = int(rider_id)
        if self.status == STATUS_PENDING:
            self.status = STATUS_ASSIGNED

    def mark_delivering(self) -> None:
        """Mark that the rider has picked up the food."""
        self.status = STATUS_DELIVERING

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and record completion metrics.

        Args:
            tick: Simulation tick at which delivery finished.
        """
        self.status = STATUS_COMPLETED
        self.completion_time = int(tick)
        self.time_taken = max(0, int(tick) - self.start_time)
        logger.info("Order %d completed at tick %d (%d ticks)", self.id, tick, self.time_taken)

    def delivery_efficiency(self) -> float:
        """Return distance covered per tick (0.0 if not yet completed)."""
        if not self.time_taken:
            return 0.0
        return self.distance / self.time_taken

    def to_dict(self) -> dict:
        """Serialise the order to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "restaurant": [self.restaurant_x, self.restaurant_y],
            "customer": [self.customer_x, self.customer_y],
            "status": self.status,
            "assigned_rider_id": self.assigned_rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "route": [list(p) for p in self.route],
        }
