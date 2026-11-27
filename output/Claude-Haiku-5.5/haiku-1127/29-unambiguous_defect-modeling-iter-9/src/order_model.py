"""Order data model and coordinate normalisation."""

import logging
from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from config import CELL_SIZE, MAP_SIZE

logger = logging.getLogger(__name__)

Point = Tuple[int, int]


def _validate_coordinate(value: Any, label: str) -> int:
    """Validate that ``value`` is an integer in the map range.

    Args:
        value: Raw coordinate value.
        label: Name used in error messages.

    Returns:
        The coordinate as an ``int``.

    Raises:
        TypeError: If ``value`` is not an integer.
        ValueError: If ``value`` is outside 0..MAP_SIZE.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer, got {value!r}")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"{label} must be within 0..{MAP_SIZE}, got {value}")
    return value


def to_cell_center(value: int) -> int:
    """Map a raw coordinate to the centre of its 100-unit grid cell.

    Out-of-range values are clamped to the map before conversion, so 800 maps
    to the centre of the last cell (750).

    Args:
        value: Coordinate in 0..800.

    Returns:
        ``(clamped // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2``.
    """
    clamped = min(max(int(value), 0), MAP_SIZE - 1)
    return (clamped // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2


def _next_order_id() -> int:
    """Return the next unique order identifier and store the counter."""
    value = globalvar.get_value("order_id_counter", 0) + 1
    globalvar.set_value("order_id_counter", value)
    return value


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant cell centre ``(x, y)``.
        cus_pos: Customer cell centre ``(x, y)``.
        start_time: Tick at which the order was created.
        status: One of ``created``, ``assigned``, ``picking_up``,
            ``delivering``, ``completed`` or ``cancelled``.
        rider_id: Assigned rider identifier, or None.
        completion_time: Tick at which the order was completed, or None.
        distance: Route length in units (restaurant to customer).
        time_taken: Ticks from creation to completion, or None.
    """

    STATUS_CREATED = "created"
    STATUS_ASSIGNED = "assigned"
    STATUS_PICKING_UP = "picking_up"
    STATUS_DELIVERING = "delivering"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from raw restaurant and customer coordinates.

        Args:
            res_pos: ``(x, y)`` restaurant coordinates in 0..800.
            cus_pos: ``(x, y)`` customer coordinates in 0..800.

        Raises:
            TypeError: If a coordinate is not an integer.
            ValueError: If a coordinate is out of range or the pair is malformed.
        """
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("Each location must have exactly two coordinates")
        rx = _validate_coordinate(res_pos[0], "restaurant x")
        ry = _validate_coordinate(res_pos[1], "restaurant y")
        cx = _validate_coordinate(cus_pos[0], "customer x")
        cy = _validate_coordinate(cus_pos[1], "customer y")

        self.id: int = _next_order_id()
        self.res_pos: Point = (to_cell_center(rx), to_cell_center(ry))
        self.cus_pos: Point = (to_cell_center(cx), to_cell_center(cy))
        self.start_time: int = int(globalvar.get_value("tick", 0))
        self.status: str = self.STATUS_CREATED
        self.rider_id: Optional[int] = None
        self.completion_time: Optional[int] = None
        self.distance: float = 0.0
        self.time_taken: Optional[int] = None

    @property
    def restaurant_x(self) -> int:
        """Restaurant x coordinate (cell centre)."""
        return self.res_pos[0]

    @property
    def restaurant_y(self) -> int:
        """Restaurant y coordinate (cell centre)."""
        return self.res_pos[1]

    @property
    def customer_x(self) -> int:
        """Customer x coordinate (cell centre)."""
        return self.cus_pos[0]

    @property
    def customer_y(self) -> int:
        """Customer y coordinate (cell centre)."""
        return self.cus_pos[1]

    @property
    def efficiency(self) -> Optional[float]:
        """Delivery efficiency in units per tick, or None if not completed."""
        if not self.time_taken:
            return None
        return self.distance / self.time_taken

    def assign_to(self, rider_id: int) -> None:
        """Record the assigned rider and mark the order as assigned.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = self.STATUS_ASSIGNED

    def mark_picking_up(self) -> None:
        """Mark the order as being picked up at the restaurant."""
        self.status = self.STATUS_PICKING_UP

    def mark_delivering(self) -> None:
        """Mark the order as out for delivery."""
        self.status = self.STATUS_DELIVERING

    def complete(self, tick: int) -> None:
        """Mark the order as completed and record completion data.

        Args:
            tick: Simulation tick at which delivery finished.
        """
        self.completion_time = tick
        self.time_taken = tick - self.start_time
        self.status = self.STATUS_COMPLETED

    def cancel(self) -> None:
        """Mark the order as cancelled (e.g. no rider could be found)."""
        self.status = self.STATUS_CANCELLED

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the order to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "start_time": self.start_time,
            "status": self.status,
            "rider_id": self.rider_id,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
