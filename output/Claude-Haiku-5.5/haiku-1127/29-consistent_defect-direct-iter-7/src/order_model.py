"""Order data model.

An order is placed with a restaurant position and a customer position in
the 0-800 map. Coordinates are snapped to the top-left corner of their grid
cell (a multiple of 100), which is the intersection used for pickup and
drop-off.
"""

from typing import Any, Dict, Optional, Sequence, Tuple

from path_planner import PathPlanner

CELL_SIZE = 100
GRID_CELLS = 8

Point = Tuple[int, int]

ORDER_STATUSES = ("pending", "assigned", "picking_up", "delivering", "completed")


def snap_to_grid(value: int) -> int:
    """Convert a raw coordinate to the top-left corner of its grid cell.

    Values beyond the last cell are clamped to the last cell.

    Args:
        value: Raw coordinate (0-1000).

    Returns:
        Grid-aligned coordinate (a multiple of 100 between 0 and 700).
    """
    cell = int(value) // CELL_SIZE
    cell = max(0, min(cell, GRID_CELLS - 1))
    return cell * CELL_SIZE


def snap_point(point: Sequence[int]) -> Point:
    """Snap an (x, y) point to its grid cell's top-left corner.

    Args:
        point: Raw (x, y) coordinates.

    Returns:
        Snapped (x, y) tuple.
    """
    return snap_to_grid(point[0]), snap_to_grid(point[1])


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant position (grid-snapped).
        cus_pos: Customer position (grid-snapped).
        status: One of pending, assigned, picking_up, delivering, completed.
        rider_id: ID of the assigned rider, or None.
        created_tick: Tick when the order was created.
        picked_up_tick: Tick when the rider reached the restaurant.
        completed_tick: Tick when the order was delivered.
        distance: Planned route length from restaurant to customer.
    """

    _id_counter = 0

    def __init__(
        self,
        res_pos: Sequence[int],
        cus_pos: Sequence[int],
        created_tick: int = 0,
        order_id: Optional[int] = None,
    ) -> None:
        """Create an order and snap both locations to the grid.

        Args:
            res_pos: Restaurant (x, y) location.
            cus_pos: Customer (x, y) location.
            created_tick: Simulated time of creation.
            order_id: Explicit ID (used when restoring saved state).
        """
        if order_id is None:
            Order._id_counter += 1
            order_id = Order._id_counter
        else:
            Order._id_counter = max(Order._id_counter, int(order_id))
        self.id = int(order_id)
        self.res_pos: Point = snap_point(res_pos)
        self.cus_pos: Point = snap_point(cus_pos)
        self.status = "pending"
        self.rider_id: Optional[int] = None
        self.created_tick = int(created_tick)
        self.picked_up_tick: Optional[int] = None
        self.completed_tick: Optional[int] = None
        self.distance = PathPlanner.route_length(
            self.res_pos, PathPlanner.plan(self.res_pos, self.cus_pos)
        )

    def assign_to(self, rider_id: int) -> None:
        """Record that the order has been assigned to a rider.

        Args:
            rider_id: ID of the rider receiving the order.
        """
        self.rider_id = int(rider_id)
        self.status = "assigned"

    def mark_picking_up(self) -> None:
        """Mark that the rider is heading to the restaurant."""
        self.status = "picking_up"

    def mark_picked_up(self, tick: int) -> None:
        """Mark that the rider has reached the restaurant.

        Args:
            tick: Current simulated time.
        """
        self.status = "delivering"
        self.picked_up_tick = int(tick)

    def mark_completed(self, tick: int) -> None:
        """Mark the order as delivered to the customer.

        Args:
            tick: Current simulated time.
        """
        self.status = "completed"
        self.completed_tick = int(tick)

    def time_taken(self) -> Optional[int]:
        """Return ticks from creation to delivery, or None if not completed."""
        if self.completed_tick is None:
            return None
        return self.completed_tick - self.created_tick

    def efficiency(self) -> Optional[float]:
        """Return delivery efficiency as distance units per tick.

        Returns:
            Efficiency value, or None if the order is not completed or the
            time taken is zero.
        """
        taken = self.time_taken()
        if not taken:
            return None
        return self.distance / taken

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the order to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_tick": self.created_tick,
            "picked_up_tick": self.picked_up_tick,
            "completed_tick": self.completed_tick,
            "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Order":
        """Rebuild an order from ``to_dict`` output.

        Args:
            data: Dictionary produced by ``to_dict``.

        Returns:
            Restored Order instance.
        """
        order = cls(
            data["res_pos"],
            data["cus_pos"],
            created_tick=data.get("created_tick", 0),
            order_id=data["id"],
        )
        order.status = data.get("status", "pending")
        order.rider_id = data.get("rider_id")
        order.picked_up_tick = data.get("picked_up_tick")
        order.completed_tick = data.get("completed_tick")
        order.distance = data.get("distance", order.distance)
        return order
