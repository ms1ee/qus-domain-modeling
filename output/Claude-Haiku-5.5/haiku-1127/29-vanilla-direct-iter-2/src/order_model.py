"""Order data model and coordinate conversion."""

import logging
import math
from typing import Any, Dict, List, Sequence, Tuple

import globalvar

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = 8

ORDER_PENDING = "pending"
ORDER_ASSIGNED = "assigned"
ORDER_PICKING_UP = "picking_up"
ORDER_DELIVERING = "delivering"
ORDER_COMPLETED = "completed"


def validate_coordinate(value: Any) -> int:
    """Validate a single map coordinate.

    Args:
        value: Value to validate.

    Returns:
        The coordinate as an integer.

    Raises:
        TypeError: If the value is not an integer.
        ValueError: If the value is outside the range 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"Coordinate {value!r} is not an integer")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"Coordinate {value} is outside the range 0-{MAP_SIZE}")
    return value


def to_grid_center(x: int, y: int) -> Tuple[int, int]:
    """Convert a coordinate to the center point of its grid cell.

    Uses ``center = (coord // 100) * 100 + 50`` with the cell index clamped to
    the valid 8x8 range, so that the coordinate 800 maps to the last cell.

    Args:
        x: X coordinate (0-800).
        y: Y coordinate (0-800).

    Returns:
        The ``(center_x, center_y)`` tuple.
    """
    gx = min(max(int(x) // CELL_SIZE, 0), GRID_CELLS - 1)
    gy = min(max(int(y) // CELL_SIZE, 0), GRID_CELLS - 1)
    return gx * CELL_SIZE + CELL_SIZE // 2, gy * CELL_SIZE + CELL_SIZE // 2


def _validate_point(point: Sequence[Any]) -> Tuple[int, int]:
    """Validate an ``[x, y]`` point.

    Args:
        point: Sequence of exactly two integer coordinates.

    Returns:
        The validated ``(x, y)`` tuple.

    Raises:
        TypeError: If the point is not a two-element sequence of integers.
        ValueError: If a coordinate is out of range.
    """
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise TypeError("A point must be a sequence of two integers")
    return validate_coordinate(point[0]), validate_coordinate(point[1])


def _registry() -> List["Order"]:
    """Return the global list of all orders ever created."""
    registry = globalvar.get_value("all_orders")
    if registry is None:
        registry = []
        globalvar.set_value("all_orders", registry)
    return registry


def _next_order_id() -> int:
    """Return the next unique order id."""
    value = int(globalvar.get_value("order_id_counter", 0) or 0) + 1
    globalvar.set_value("order_id_counter", value)
    return value


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        raw_restaurant: Restaurant coordinates as entered by the user.
        raw_customer: Customer coordinates as entered by the user.
        res_pos: Restaurant grid-cell center ``(x, y)``.
        cus_pos: Customer grid-cell center ``(x, y)``.
        status: One of pending, assigned, picking_up, delivering, completed.
        rider_id: Id of the assigned rider, or None.
        start_tick: Simulated time at which the order was created.
        assigned_tick: Simulated time at which the order was assigned.
        complete_tick: Simulated time at which the order was delivered.
        distance: Straight-line distance between the grid centers.
        time_taken: Ticks from creation to delivery, or None.
        efficiency: Distance covered per tick, or None.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: ``[restaurant_x, restaurant_y]`` in the range 0-800.
            cus_pos: ``[customer_x, customer_y]`` in the range 0-800.

        Raises:
            TypeError: If the coordinates are not integers.
            ValueError: If a coordinate is outside the range 0-800.
        """
        rx, ry = _validate_point(res_pos)
        cx, cy = _validate_point(cus_pos)
        self.id: int = _next_order_id()
        self.raw_restaurant: Tuple[int, int] = (rx, ry)
        self.raw_customer: Tuple[int, int] = (cx, cy)
        self.res_pos: Tuple[int, int] = to_grid_center(rx, ry)
        self.cus_pos: Tuple[int, int] = to_grid_center(cx, cy)
        self.status: str = ORDER_PENDING
        self.rider_id: Any = None
        self.start_tick: int = int(globalvar.get_value("tick", 0) or 0)
        self.assigned_tick: Any = None
        self.complete_tick: Any = None
        self.distance: float = round(
            math.hypot(self.res_pos[0] - self.cus_pos[0],
                       self.res_pos[1] - self.cus_pos[1]), 2)
        self.time_taken: Any = None
        self.efficiency: Any = None
        _registry().append(self)
        logger.info("Order #%d created: restaurant=%s customer=%s",
                    self.id, self.res_pos, self.cus_pos)

    def assign_to(self, rider_id: int) -> None:
        """Assign this order to a rider.

        The order is appended to the rider's ``orders`` list through
        ``Rider.accept_order``, which also performs the idle-to-picking-up
        state transition and writes the log entry.

        Args:
            rider_id: Identifier of the target rider.

        Raises:
            ValueError: If no rider with the given id exists.
        """
        riders = globalvar.get_value("riders") or []
        rider = next((r for r in riders if r.rider_id == rider_id), None)
        if rider is None:
            raise ValueError(f"No rider with id {rider_id}")
        self.rider_id = rider_id
        self.assigned_tick = int(globalvar.get_value("tick", 0) or 0)
        self.status = ORDER_ASSIGNED
        rider.accept_order(self)
        logger.info("Order #%d assigned to rider #%d", self.id, rider_id)

    def mark_completed(self, tick: int) -> None:
        """Record delivery completion, time taken and efficiency.

        Args:
            tick: Simulated time of delivery.
        """
        self.status = ORDER_COMPLETED
        self.complete_tick = tick
        self.time_taken = max(tick - self.start_tick, 0)
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 3)
        else:
            self.efficiency = self.distance
        logger.info("Order #%d completed at tick %d", self.id, tick)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the order.

        Returns:
            Dictionary with the order attributes.
        """
        return {
            "id": self.id,
            "restaurant": list(self.raw_restaurant),
            "customer": list(self.raw_customer),
            "restaurant_grid": list(self.res_pos),
            "customer_grid": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_tick": self.start_tick,
            "assigned_tick": self.assigned_tick,
            "complete_tick": self.complete_tick,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
