"""Order data model and coordinate conversion helpers.

User input coordinates (0-800) are snapped to the top-left corner of the
100x100 grid cell that contains them. Cell index is clamped to the 8x8 grid.
"""

import itertools
from typing import Any, Dict, Optional, Tuple

import globalvar

GRID_CELL_SIZE = 100
GRID_CELLS = 8
MAX_CELL_INDEX = GRID_CELLS - 1

_id_counter = itertools.count(1)


def snap_to_cell(value: int) -> int:
    """Convert a coordinate to the top-left corner of its grid cell.

    Args:
        value: Input coordinate on one axis.

    Returns:
        Grid coordinate (multiple of 100) of the containing cell.
    """
    v = max(0, int(value))
    index = min(v // GRID_CELL_SIZE, MAX_CELL_INDEX)
    return index * GRID_CELL_SIZE


def to_grid_cell(x: int, y: int) -> Tuple[int, int]:
    """Convert an input coordinate pair to its grid cell top-left corner.

    Args:
        x: Input x coordinate.
        y: Input y coordinate.

    Returns:
        Tuple ``(grid_x, grid_y)``.
    """
    return snap_to_cell(x), snap_to_cell(y)


def cell_center(grid_x: int, grid_y: int) -> Tuple[int, int]:
    """Return the center point of the cell whose top-left corner is given.

    Uses ``center_x = (grid_x // 100) * 100 + 50``.

    Args:
        grid_x: X coordinate of the cell.
        grid_y: Y coordinate of the cell.

    Returns:
        Tuple ``(center_x, center_y)``.
    """
    return (grid_x // GRID_CELL_SIZE) * GRID_CELL_SIZE + 50, \
        (grid_y // GRID_CELL_SIZE) * GRID_CELL_SIZE + 50


def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: First point.
        b: Second point.

    Returns:
        ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant grid position (top-left of its cell).
        cus_pos: Customer grid position (top-left of its cell).
        status: One of ``"created"``, ``"assigned"``, ``"picked_up"``,
            ``"completed"``.
        rider_id: ID of the assigned rider, or None.
        start_time: Tick at which the order was created.
        distance: Manhattan distance from restaurant to customer.
        completion_time: Tick at which delivery finished, or None.
        time_taken: Ticks between creation and completion, or None.
        efficiency: Distance covered per tick, or None.
    """

    CREATED = "created"
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    COMPLETED = "completed"

    def __init__(self, res_pos: Tuple[int, int],
                 cus_pos: Tuple[int, int]) -> None:
        """Create an order from raw input coordinates.

        Args:
            res_pos: Restaurant coordinate ``(x, y)``.
            cus_pos: Customer coordinate ``(x, y)``.
        """
        self.id: int = next(_id_counter)
        self.res_pos: Tuple[int, int] = to_grid_cell(*res_pos)
        self.cus_pos: Tuple[int, int] = to_grid_cell(*cus_pos)
        self.status: str = self.CREATED
        self.rider_id: Optional[int] = None
        self.start_time: int = globalvar.get_value("tick", 0) or 0
        self.distance: int = manhattan(self.res_pos, self.cus_pos)
        self.completion_time: Optional[int] = None
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = self.ASSIGNED

    def mark_picked_up(self) -> None:
        """Mark the order as picked up at the restaurant."""
        self.status = self.PICKED_UP

    def mark_completed(self, tick: int) -> None:
        """Mark the order as delivered and record efficiency data.

        Args:
            tick: Current simulated tick at delivery time.
        """
        self.status = self.COMPLETED
        self.completion_time = tick
        self.time_taken = max(0, tick - self.start_time)
        self.efficiency = self.distance / max(1, self.time_taken)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the order to a JSON-compatible dictionary.

        Returns:
            Dictionary representation of the order.
        """
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "distance": self.distance,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
