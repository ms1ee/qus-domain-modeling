"""Order data model.

An Order stores the restaurant and customer locations (converted to the top-left
corner of their grid cell), its lifecycle status and delivery statistics.
"""

import logging
from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar

logger = logging.getLogger(__name__)

MAP_SIZE = 800
GRID_CELL_SIZE = 100
COORD_MIN = 0
COORD_MAX = 1000


def snap_to_grid(value: int) -> int:
    """Convert a coordinate to the top-left corner of its grid cell.

    Values outside the map are clamped into [0, MAP_SIZE] first, so abnormal
    input never produces an invalid location.

    Args:
        value: Raw coordinate supplied by the user.

    Returns:
        Coordinate of the top-left corner of the containing cell.
    """
    clamped = max(0, min(int(value), MAP_SIZE))
    return (clamped // GRID_CELL_SIZE) * GRID_CELL_SIZE


def _next_order_id() -> int:
    """Generate the next unique order identifier.

    Returns:
        Integer id, strictly increasing across the run.
    """
    counter = (globalvar.get_value("order_id_counter", 0) or 0) + 1
    globalvar.set_value("order_id_counter", counter)
    return counter


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        order_id: Alias of ``id``.
        restaurant_x / restaurant_y: Restaurant grid corner coordinates.
        customer_x / customer_y: Customer grid corner coordinates.
        start_time: Tick at which the order was created.
        completion_time: Tick at which delivery finished (None until then).
        distance: Manhattan distance from restaurant to customer.
        time_taken: Ticks between creation and completion (None until then).
        efficiency: Distance covered per tick for the completed order.
        status: "pending", "assigned", "picking_up", "delivering" or "completed".
        rider_id: Identifier of the assigned rider, or None.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from restaurant and customer positions.

        Args:
            res_pos: (x, y) of the restaurant, range 0-800.
            cus_pos: (x, y) of the customer, range 0-800.
        """
        rx, ry = res_pos
        cx, cy = cus_pos
        self.id = _next_order_id()
        self.order_id = self.id
        self.restaurant_x = snap_to_grid(rx)
        self.restaurant_y = snap_to_grid(ry)
        self.customer_x = snap_to_grid(cx)
        self.customer_y = snap_to_grid(cy)
        self.start_time = int(globalvar.get_value("time", 0) or 0)
        self.completion_time: Optional[int] = None
        self.distance = float(
            abs(self.customer_x - self.restaurant_x)
            + abs(self.customer_y - self.restaurant_y)
        )
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None
        self.status = "pending"
        self.rider_id: Optional[int] = None
        logger.info("Order %d created: restaurant=%s customer=%s",
                    self.id, self.restaurant_pos, self.customer_pos)

    @property
    def restaurant_pos(self) -> Tuple[int, int]:
        """Restaurant grid corner as a tuple."""
        return (self.restaurant_x, self.restaurant_y)

    @property
    def customer_pos(self) -> Tuple[int, int]:
        """Customer grid corner as a tuple."""
        return (self.customer_x, self.customer_y)

    def assign_to(self, rider_id: int) -> None:
        """Assign this order to a rider by appending it to the rider's orders.

        Args:
            rider_id: Identifier of the rider receiving the order.

        Raises:
            ValueError: If the rider does not exist or the order is already
                assigned or completed.
        """
        if self.status == "completed":
            raise ValueError(f"Order {self.id} is already completed.")
        if self.rider_id is not None:
            raise ValueError(f"Order {self.id} is already assigned to rider {self.rider_id}.")
        riders = globalvar.get_value("riders", []) or []
        rider = next((r for r in riders if r.rider_id == rider_id), None)
        if rider is None:
            raise ValueError(f"Rider {rider_id} does not exist.")
        rider.orders.append(self)
        self.rider_id = rider_id
        self.status = "assigned"
        logger.info("Order %d assigned to rider %d", self.id, rider_id)

    def complete(self, time: int) -> None:
        """Mark the order as delivered and record completion statistics.

        Args:
            time: Tick at which delivery finished.
        """
        self.completion_time = time
        self.time_taken = max(0, time - self.start_time)
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 3)
        else:
            self.efficiency = self.distance
        self.status = "completed"
        logger.info("Order %d completed at tick %d", self.id, time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the order to a JSON-compatible dictionary.

        Returns:
            Dictionary describing the order.
        """
        return {
            "id": self.id,
            "restaurant": list(self.restaurant_pos),
            "customer": list(self.customer_pos),
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
            "status": self.status,
            "rider_id": self.rider_id,
        }
