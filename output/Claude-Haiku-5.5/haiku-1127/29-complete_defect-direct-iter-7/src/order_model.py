"""Order data model, coordinate validation and grid-cell conversion."""

from __future__ import annotations

import itertools
import logging
from typing import Any

import config

logger = logging.getLogger("dispatch.order_model")

STATUS_CREATED = "created"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"
VALID_STATUSES = (
    STATUS_CREATED,
    STATUS_ASSIGNED,
    STATUS_PICKING_UP,
    STATUS_DELIVERING,
    STATUS_COMPLETED,
)

_ORDER_IDS = itertools.count(1)


def validate_coordinate(value: Any) -> int:
    """Validate a single map coordinate.

    Args:
        value: Candidate coordinate.

    Returns:
        int: The validated coordinate.

    Raises:
        ValueError: If the value is not an integer in the range 0-MAP_SIZE.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"coordinate must be an integer, got {value!r}")
    if not 0 <= value <= config.MAP_SIZE:
        raise ValueError(
            f"coordinate {value} is outside the range 0-{config.MAP_SIZE}"
        )
    return value


def validate_point(point: Any) -> tuple[int, int]:
    """Validate an (x, y) point.

    Args:
        point: Iterable with exactly two coordinates.

    Returns:
        tuple[int, int]: The validated point.

    Raises:
        ValueError: If the point is malformed or out of range.
    """
    try:
        x, y = point
    except (TypeError, ValueError):
        raise ValueError("a point must contain exactly two coordinates")
    return validate_coordinate(x), validate_coordinate(y)


def grid_index(x: int, y: int) -> tuple[int, int]:
    """Return the (gx, gy) grid cell containing a map coordinate.

    Coordinates on the far boundary (e.g. 800) are assigned to the last cell.

    Args:
        x: Map x coordinate.
        y: Map y coordinate.

    Returns:
        tuple[int, int]: Grid column and row indices, each in 0..GRID_SIZE-1.
    """
    gx = min(max(int(x), 0) // config.CELL_SIZE, config.GRID_SIZE - 1)
    gy = min(max(int(y), 0) // config.CELL_SIZE, config.GRID_SIZE - 1)
    return gx, gy


def to_grid_center(x: int, y: int) -> tuple[int, int]:
    """Convert a map coordinate to the centre point of its grid cell.

    Implements ``center = (grid // 100) * 100 + 50`` for each axis.

    Args:
        x: Map x coordinate.
        y: Map y coordinate.

    Returns:
        tuple[int, int]: Centre point of the containing cell.
    """
    gx, gy = grid_index(x, y)
    half = config.CELL_SIZE // 2
    return gx * config.CELL_SIZE + half, gy * config.CELL_SIZE + half


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: First point.
        b: Second point.

    Returns:
        int: |ax - bx| + |ay - by|.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        raw_restaurant: Restaurant coordinates as entered by the user.
        raw_customer: Customer coordinates as entered by the user.
        res_pos: Restaurant grid-cell centre.
        cus_pos: Customer grid-cell centre.
        status: One of the STATUS_* constants.
        rider_id: Identifier of the assigned rider, or None.
        start_tick: Tick at which the order was created.
        accept_tick: Tick at which the rider accepted the order.
        pickup_tick: Tick at which the rider reached the restaurant.
        complete_tick: Tick at which the order was delivered.
        distance: Restaurant-to-customer distance in map units.
        pickup_distance: Rider-to-restaurant distance at assignment time.
        estimated_ticks: Estimated ticks for the full route at assignment.
    """

    def __init__(self, res_pos, cus_pos, start_tick: int = 0) -> None:
        """Create an order from raw map coordinates.

        Args:
            res_pos: Restaurant (x, y), each in 0-800.
            cus_pos: Customer (x, y), each in 0-800.
            start_tick: Simulated tick of creation.

        Raises:
            ValueError: If either point is malformed or out of range.
        """
        raw_res = validate_point(res_pos)
        raw_cus = validate_point(cus_pos)
        self.id = next(_ORDER_IDS)
        self.raw_restaurant = raw_res
        self.raw_customer = raw_cus
        self.res_pos = to_grid_center(*raw_res)
        self.cus_pos = to_grid_center(*raw_cus)
        self.status = STATUS_CREATED
        self.rider_id = None
        self.start_tick = int(start_tick)
        self.accept_tick = None
        self.pickup_tick = None
        self.complete_tick = None
        self.distance = manhattan(self.res_pos, self.cus_pos)
        self.pickup_distance = 0
        self.estimated_ticks = 0
        logger.debug("Order %d created: %s -> %s", self.id,
                     self.res_pos, self.cus_pos)

    def assign_to(self, rider_id: int) -> None:
        """Record the rider assigned to this order.

        The caller is responsible for appending the order to the rider's
        ``orders`` list.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        if self.status == STATUS_CREATED:
            self.status = STATUS_ASSIGNED
        logger.info("Order %d assigned to rider %d", self.id, rider_id)

    def mark_status(self, status: str) -> None:
        """Update the lifecycle status.

        Args:
            status: One of the STATUS_* constants.

        Raises:
            ValueError: If the status is unknown.
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"unknown order status {status!r}")
        self.status = status

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and record the completion time.

        Args:
            tick: Simulated tick of delivery.
        """
        self.status = STATUS_COMPLETED
        self.complete_tick = int(tick)
        logger.info("Order %d completed at tick %d (time taken %s)",
                    self.id, self.complete_tick, self.time_taken)

    @property
    def time_taken(self) -> int | None:
        """Ticks from creation to delivery, or None if not yet delivered."""
        if self.complete_tick is None:
            return None
        return self.complete_tick - self.start_tick

    @property
    def efficiency(self) -> float | None:
        """Delivery efficiency as distance units per tick, or None."""
        taken = self.time_taken
        if not taken:
            return None
        return round(self.distance / taken, 2)

    def to_dict(self) -> dict:
        """Serialise the order to a JSON-compatible dictionary.

        Returns:
            dict: Order details.
        """
        return {
            "id": self.id,
            "status": self.status,
            "restaurant": list(self.raw_restaurant),
            "customer": list(self.raw_customer),
            "restaurant_cell": list(self.res_pos),
            "customer_cell": list(self.cus_pos),
            "rider_id": self.rider_id,
            "start_tick": self.start_tick,
            "accept_tick": self.accept_tick,
            "pickup_tick": self.pickup_tick,
            "complete_tick": self.complete_tick,
            "distance": self.distance,
            "pickup_distance": self.pickup_distance,
            "estimated_ticks": self.estimated_ticks,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
