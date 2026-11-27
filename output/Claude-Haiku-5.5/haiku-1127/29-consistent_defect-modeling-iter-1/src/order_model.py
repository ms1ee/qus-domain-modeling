"""Order data model."""

import itertools
from typing import Any, Dict, Optional, Sequence, Tuple

Point = Tuple[int, int]

VALID_STATUSES = ("pending", "assigned", "picking_up", "delivering", "completed")

_ORDER_IDS = itertools.count(1)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant grid coordinate (x, y).
        cus_pos: Customer grid coordinate (x, y).
        start_time: Simulated tick when the order was created.
        completion_time: Simulated tick when delivery finished, or None.
        rider_id: Identifier of the assigned rider, or None.
        status: One of pending, assigned, picking_up, delivering, completed.
        distance: Manhattan distance restaurant -> customer.
        time_taken: Ticks from creation to completion, or None.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int], start_time: int = 0) -> None:
        self.id: int = next(_ORDER_IDS)
        self.res_pos: Point = (int(res_pos[0]), int(res_pos[1]))
        self.cus_pos: Point = (int(cus_pos[0]), int(cus_pos[1]))
        self.start_time: int = int(start_time)
        self.completion_time: Optional[int] = None
        self.rider_id: Optional[int] = None
        self.status: str = "pending"
        self.distance: float = float(
            abs(self.res_pos[0] - self.cus_pos[0]) + abs(self.res_pos[1] - self.cus_pos[1])
        )
        self.time_taken: Optional[int] = None

    @property
    def restaurant_x(self) -> int:
        """Restaurant x coordinate."""
        return self.res_pos[0]

    @property
    def restaurant_y(self) -> int:
        """Restaurant y coordinate."""
        return self.res_pos[1]

    @property
    def customer_x(self) -> int:
        """Customer x coordinate."""
        return self.cus_pos[0]

    @property
    def customer_y(self) -> int:
        """Customer y coordinate."""
        return self.cus_pos[1]

    @property
    def efficiency(self) -> float:
        """Delivery efficiency: distance covered per tick (0.0 if unknown)."""
        if not self.time_taken:
            return 0.0
        return self.distance / self.time_taken

    def assign_to(self, rider_id: int) -> None:
        """Bind the order to a rider and mark it as assigned.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = int(rider_id)
        self.status = "assigned"

    def set_status(self, status: str) -> None:
        """Update the lifecycle status.

        Raises:
            ValueError: If the status is not recognised.
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid order status: {status}")
        self.status = status

    def complete(self, completion_time: int) -> None:
        """Mark the order as delivered and record efficiency data.

        Args:
            completion_time: Simulated tick at which delivery finished.
        """
        self.status = "completed"
        self.completion_time = int(completion_time)
        self.time_taken = max(0, self.completion_time - self.start_time)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "rider_id": self.rider_id,
            "status": self.status,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self) -> str:
        return f"Order(id={self.id}, status={self.status}, rider={self.rider_id})"
