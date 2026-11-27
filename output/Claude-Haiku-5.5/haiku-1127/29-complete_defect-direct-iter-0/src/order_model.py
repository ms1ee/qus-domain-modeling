"""Order data model.

An order is created from user input ``[restaurant_x, restaurant_y,
customer_x, customer_y]`` (each 0-800). Coordinates are converted to grid
cell centers for routing.
"""

from typing import Any, Dict, Optional, Sequence

import globalvar
from grid import (
    Point,
    cell_index,
    manhattan,
    to_grid_center,
    validate_coordinate,
)

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKED_UP = "picked_up"
STATUS_COMPLETED = "completed"


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Raw restaurant coordinate as entered by the user.
        cus_pos: Raw customer coordinate as entered by the user.
        restaurant_cell / customer_cell: Grid cell indices (column, row).
        restaurant_center / customer_center: Routing targets (cell centers).
        distance: Manhattan distance between the two centers.
        status: One of "pending", "assigned", "picked_up", "completed".
        rider_id: ID of the assigned rider, or None.
        start_time: Tick when the order was created.
        assigned_time / pickup_time / completed_time: Event ticks.
        time_taken: Ticks from creation to completion.
        efficiency: Distance covered per tick (units/tick).
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: ``(x, y)`` restaurant coordinate, each 0-800.
            cus_pos: ``(x, y)`` customer coordinate, each 0-800.

        Raises:
            ValueError: If a coordinate is invalid.
        """
        rx, ry = self._parse_point(res_pos, "restaurant")
        cx, cy = self._parse_point(cus_pos, "customer")
        self.id: int = globalvar.next_counter("order_id_counter")
        self.res_pos: Point = (rx, ry)
        self.cus_pos: Point = (cx, cy)
        self.restaurant_cell: Point = (cell_index(rx), cell_index(ry))
        self.customer_cell: Point = (cell_index(cx), cell_index(cy))
        self.restaurant_center: Point = to_grid_center(rx, ry)
        self.customer_center: Point = to_grid_center(cx, cy)
        self.distance: int = manhattan(
            self.restaurant_center, self.customer_center
        )
        self.status: str = STATUS_PENDING
        self.rider_id: Optional[int] = None
        self.start_time: int = int(globalvar.get_value("tick", 0))
        self.assigned_time: Optional[int] = None
        self.pickup_time: Optional[int] = None
        self.completed_time: Optional[int] = None
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None

    @staticmethod
    def _parse_point(point: Sequence[int], label: str) -> Point:
        """Validate a two-element coordinate sequence.

        Args:
            point: Sequence containing x and y.
            label: Name used in error messages.

        Returns:
            Validated ``(x, y)`` tuple.

        Raises:
            ValueError: If the sequence length or values are invalid.
        """
        if len(point) != 2:
            raise ValueError(f"{label} position must have exactly 2 values")
        x = validate_coordinate(point[0], f"{label} x")
        y = validate_coordinate(point[1], f"{label} y")
        return (x, y)

    def assign_to(self, rider_id: int) -> None:
        """Record that the order has been assigned to a rider.

        The caller is responsible for appending the order to the rider's
        ``orders`` list.

        Args:
            rider_id: ID of the rider receiving the order.

        Raises:
            RuntimeError: If the order is not pending.
        """
        if self.status != STATUS_PENDING:
            raise RuntimeError(
                f"order {self.id} cannot be assigned from status {self.status}"
            )
        self.rider_id = rider_id
        self.assigned_time = int(globalvar.get_value("tick", 0))
        self.status = STATUS_ASSIGNED

    def mark_picked_up(self, time: int) -> None:
        """Mark that the rider reached the restaurant and collected the food.

        Args:
            time: Simulated tick of the pickup.
        """
        self.status = STATUS_PICKED_UP
        self.pickup_time = time

    def complete(self, time: int) -> None:
        """Mark the order as delivered and compute efficiency metrics.

        Args:
            time: Simulated tick of the delivery.
        """
        self.status = STATUS_COMPLETED
        self.completed_time = time
        self.time_taken = max(0, time - self.start_time)
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 2)
        else:
            self.efficiency = float(self.distance)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "status": self.status,
            "restaurant_input": list(self.res_pos),
            "customer_input": list(self.cus_pos),
            "restaurant_center": list(self.restaurant_center),
            "customer_center": list(self.customer_center),
            "distance": self.distance,
            "start_time": self.start_time,
            "assigned_time": self.assigned_time,
            "pickup_time": self.pickup_time,
            "completed_time": self.completed_time,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
            "rider_id": self.rider_id,
        }
