"""Order data model: validation, grid snapping and order lifecycle."""

import itertools
import logging

import globalvar
from path_planner import is_valid_coordinate, manhattan_distance, snap_to_grid

logger = logging.getLogger(__name__)

PENDING = "pending"
ASSIGNED = "assigned"
PICKED_UP = "picked_up"
COMPLETED = "completed"


def _now():
    """Return the current simulated tick (0 if unset)."""
    return globalvar.get_value("tick") or 0


def _parse_point(point, label):
    """Validate an ``(x, y)`` pair and snap it to its grid cell.

    Args:
        point: Two-element sequence of integers in range 0-1000.
        label: Human-readable name used in error messages.

    Returns:
        tuple[int, int]: Top-left corner of the grid cell containing the point.

    Raises:
        ValueError: If the point is malformed or out of range.
    """
    try:
        x, y = point
    except (TypeError, ValueError):
        raise ValueError(f"{label} location must be an (x, y) pair")
    for value in (x, y):
        if not is_valid_coordinate(value):
            raise ValueError(
                f"{label} coordinate {value!r} must be an integer in 0-1000")
    return snap_to_grid(x), snap_to_grid(y)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant grid point ``(x, y)`` (cell top-left).
        cus_pos: Customer grid point ``(x, y)`` (cell top-left).
        status: One of ``"pending"``, ``"assigned"``, ``"picked_up"``,
            ``"completed"``.
        rider_id: Id of the assigned rider, or None.
        created_tick: Tick at which the order was created.
        assigned_tick: Tick of assignment, or None.
        pickup_tick: Tick of pickup, or None.
        completed_tick: Tick of delivery, or None.
        distance: Manhattan distance restaurant to customer.
    """

    _id_sequence = itertools.count(1)

    def __init__(self, res_pos, cus_pos, created_tick=None, order_id=None):
        """Create an order from raw coordinates.

        Args:
            res_pos: Restaurant ``(x, y)`` in range 0-1000.
            cus_pos: Customer ``(x, y)`` in range 0-1000.
            created_tick: Optional creation tick; defaults to current tick.
            order_id: Optional fixed id (used when restoring state).

        Raises:
            ValueError: If coordinates are invalid.
        """
        self.res_pos = _parse_point(res_pos, "restaurant")
        self.cus_pos = _parse_point(cus_pos, "customer")
        if order_id is None:
            order_id = next(Order._id_sequence)
        self.id = order_id
        self.status = PENDING
        self.rider_id = None
        self.created_tick = created_tick if created_tick is not None else _now()
        self.assigned_tick = None
        self.pickup_tick = None
        self.completed_tick = None
        self.distance = manhattan_distance(self.res_pos[0], self.res_pos[1],
                                           self.cus_pos[0], self.cus_pos[1])
        logger.info("Order #%d created: %s -> %s", self.id,
                    self.res_pos, self.cus_pos)

    @classmethod
    def set_next_id(cls, next_id):
        """Set the next identifier to be issued.

        Args:
            next_id: The next integer id to use.

        Returns:
            None
        """
        cls._id_sequence = itertools.count(next_id)

    def assign_to(self, rider_id):
        """Assign this order to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.

        Returns:
            None

        Raises:
            ValueError: If the order is not pending.
        """
        if self.status != PENDING:
            raise ValueError(f"Order #{self.id} is already {self.status}")
        self.rider_id = rider_id
        self.status = ASSIGNED
        self.assigned_tick = _now()
        logger.info("Order #%d assigned to rider #%s", self.id, rider_id)

    def mark_picked_up(self, tick):
        """Record that the rider collected the order.

        Args:
            tick: Simulated time of pickup.

        Returns:
            None
        """
        self.status = PICKED_UP
        self.pickup_tick = tick

    def mark_completed(self, tick):
        """Record delivery completion; the order stays in history.

        Args:
            tick: Simulated time of delivery.

        Returns:
            None
        """
        self.status = COMPLETED
        self.completed_tick = tick
        logger.info("Order #%d completed at tick %d", self.id, tick)

    def time_taken(self):
        """Return ticks from creation to completion.

        Returns:
            int or None: Elapsed ticks, or None if not completed.
        """
        if self.completed_tick is None:
            return None
        return self.completed_tick - self.created_tick

    def efficiency(self):
        """Return delivery efficiency as distance units per tick.

        Returns:
            float or None: ``distance / time_taken``, or None if unavailable.
        """
        elapsed = self.time_taken()
        if not elapsed:
            return None
        return self.distance / elapsed

    def coordinates(self):
        """Return the order in ``[restaurant_x, restaurant_y, customer_x,
        customer_y]`` format.

        Returns:
            list[int]: Four-element coordinate list.
        """
        return [self.res_pos[0], self.res_pos[1],
                self.cus_pos[0], self.cus_pos[1]]

    def to_dict(self):
        """Serialise the order to a JSON-compatible dictionary.

        Returns:
            dict: Order fields.
        """
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_tick": self.created_tick,
            "assigned_tick": self.assigned_tick,
            "pickup_tick": self.pickup_tick,
            "completed_tick": self.completed_tick,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from :meth:`to_dict` output.

        Args:
            data: Dictionary produced by :meth:`to_dict`.

        Returns:
            Order: Restored order.
        """
        order = cls(data["res_pos"], data["cus_pos"],
                    created_tick=data.get("created_tick", 0),
                    order_id=data["id"])
        order.status = data.get("status", PENDING)
        order.rider_id = data.get("rider_id")
        order.assigned_tick = data.get("assigned_tick")
        order.pickup_tick = data.get("pickup_tick")
        order.completed_tick = data.get("completed_tick")
        return order
