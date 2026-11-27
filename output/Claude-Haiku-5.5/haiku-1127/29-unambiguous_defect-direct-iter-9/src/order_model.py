"""Order data model: coordinate validation, snapping and lifecycle."""

import itertools
from typing import Any, Dict, List, Optional, Tuple

from config import CELL_SIZE, MAP_SIZE, is_valid_coordinate
from path_planner import PathPlanner

Point = Tuple[int, int]

_ORDER_IDS = itertools.count(1)


def snap_coordinate(value: int) -> int:
    """Snap a single coordinate to the nearest street line (multiple of 100).

    Restaurant and customer locations are placed on street intersections,
    which matches the rule that integer hundreds denote these locations.
    The result is clamped to the map range.

    Args:
        value: Integer coordinate in ``[0, MAP_SIZE]``.

    Returns:
        The snapped coordinate.
    """
    snapped = int(round(value / CELL_SIZE)) * CELL_SIZE
    return min(max(snapped, 0), MAP_SIZE)


def snap_point(point: Point) -> Point:
    """Snap both coordinates of a point to the nearest intersection."""
    return snap_coordinate(point[0]), snap_coordinate(point[1])


def _validate_point(point: Any, label: str) -> Point:
    """Validate that ``point`` is a pair of in-range integers.

    Raises:
        ValueError: If the structure or the values are invalid.
    """
    try:
        x, y = point
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a pair of integers")
    for value in (x, y):
        if not is_valid_coordinate(value):
            raise ValueError(f"{label} coordinate {value} is outside 0-{MAP_SIZE}")
    return x, y


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique, auto-incremented order identifier.
        raw_input: The original input ``[rx, ry, cx, cy]``.
        res_pos: Snapped restaurant location ``(x, y)``.
        cus_pos: Snapped customer location ``(x, y)``.
        status: One of ``created``, ``assigned``, ``picking_up``,
            ``delivering``, ``completed`` or ``rejected``.
        rider_id: Identifier of the assigned rider, or None.
        created_tick: Simulated time when the order was created.
        completed_tick: Simulated time of delivery, or None.
        distance: Route length from restaurant to customer.
        time_taken: Ticks from creation to completion, or None.
        efficiency: Distance per tick for the completed order, or None.
    """

    def __init__(self, res_pos: Any, cus_pos: Any, created_tick: int = 0) -> None:
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: ``(x, y)`` restaurant coordinates in 0-800.
            cus_pos: ``(x, y)`` customer coordinates in 0-800.
            created_tick: Simulated time at creation.

        Raises:
            ValueError: If coordinates are malformed or out of range.
        """
        raw_res = _validate_point(res_pos, "restaurant")
        raw_cus = _validate_point(cus_pos, "customer")
        self.id = next(_ORDER_IDS)
        self.raw_input: List[int] = [raw_res[0], raw_res[1], raw_cus[0], raw_cus[1]]
        self.res_pos: Point = snap_point(raw_res)
        self.cus_pos: Point = snap_point(raw_cus)
        self.status = "created"
        self.rider_id: Optional[int] = None
        self.created_tick = created_tick
        self.pickup_started_tick: Optional[int] = None
        self.delivery_started_tick: Optional[int] = None
        self.completed_tick: Optional[int] = None
        self.distance = PathPlanner().route_length(
            self.res_pos,
            PathPlanner().plan(self.res_pos, self.cus_pos),
        )
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None

    def as_list(self) -> List[int]:
        """Return the snapped order as ``[rx, ry, cx, cy]``."""
        return [self.res_pos[0], self.res_pos[1], self.cus_pos[0], self.cus_pos[1]]

    def assign_to(self, rider_id: int) -> None:
        """Assign this order to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = "assigned"

    def mark_picking_up(self, tick: int) -> None:
        """Record that the rider has started travelling to the restaurant."""
        self.status = "picking_up"
        self.pickup_started_tick = tick

    def mark_delivering(self, tick: int) -> None:
        """Record that the food has been collected and delivery has started."""
        self.status = "delivering"
        self.delivery_started_tick = tick

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and compute efficiency metrics.

        Args:
            tick: Simulated time of delivery.
        """
        self.status = "completed"
        self.completed_tick = tick
        self.time_taken = max(tick - self.created_tick, 0)
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 2)
        else:
            self.efficiency = float(self.distance)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_tick": self.created_tick,
            "completed_tick": self.completed_tick,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }

    def __repr__(self) -> str:
        return (f"Order(id={self.id}, res={self.res_pos}, cus={self.cus_pos}, "
                f"status={self.status})")
