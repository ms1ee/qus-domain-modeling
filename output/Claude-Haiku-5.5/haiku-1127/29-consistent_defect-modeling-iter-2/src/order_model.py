"""Order data model.

An order is described by a restaurant position and a customer position,
both snapped to the top-left corner of their grid cell on creation.
"""

import itertools
import logging

import globalvar
from grid_map import GridMap

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"

_GRID = GridMap()
_ORDER_IDS = itertools.count(1)


def _current_tick():
    """Return the simulated time stored in the global table."""
    return globalvar.get_value("tick") or 0


def _validate_point(point, label):
    """Validate an ``(x, y)`` integer pair and return it as a tuple.

    Raises:
        ValueError: If the point does not contain exactly two values.
        TypeError: If the values are not integers.
    """
    values = list(point)
    if len(values) != 2:
        raise ValueError(f"{label} position must have exactly 2 coordinates")
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{label} coordinates must be integers")
    return int(values[0]), int(values[1])


def snap_to_grid(x, y):
    """Convert raw coordinates to the top-left corner of their grid cell.

    Out-of-range values are clamped to the map before snapping.
    """
    return _GRID.snap_point(x, y)


class Order:
    """A food delivery order.

    Attributes:
        id: Unique integer identifier.
        res_pos: Restaurant ``(x, y)`` after grid snapping.
        cus_pos: Customer ``(x, y)`` after grid snapping.
        status: One of pending, assigned, picking_up, delivering, completed.
        rider_id: ID of the assigned rider, or None.
        start_time: Tick at which the order was created.
        completion_time: Tick at which delivery finished, or None.
        distance: Manhattan distance restaurant -> customer.
        time_taken: Ticks between creation and completion, or None.
        efficiency: Distance covered per tick, or None until completed.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order.

        Args:
            res_pos: ``(x, y)`` restaurant position (integers, 0-800).
            cus_pos: ``(x, y)`` customer position (integers, 0-800).

        Raises:
            ValueError: If a position does not have exactly two coordinates.
            TypeError: If a coordinate is not an integer.
        """
        raw_res = _validate_point(res_pos, "restaurant")
        raw_cus = _validate_point(cus_pos, "customer")
        self.id = next(_ORDER_IDS)
        self.res_pos = snap_to_grid(*raw_res)
        self.cus_pos = snap_to_grid(*raw_cus)
        self.status = STATUS_PENDING
        self.rider_id = None
        self.start_time = _current_tick()
        self.completion_time = None
        self.distance = float(
            abs(self.res_pos[0] - self.cus_pos[0])
            + abs(self.res_pos[1] - self.cus_pos[1])
        )
        self.time_taken = None
        self.efficiency = None
        logger.debug("Created order %d", self.id)

    @property
    def order_id(self):
        """Alias of :attr:`id`."""
        return self.id

    def assign_to(self, rider_id):
        """Record the rider this order is assigned to.

        The caller is responsible for appending the order to
        ``rider.orders``.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_picking_up(self):
        """Mark the order as being picked up by its rider."""
        self.status = STATUS_PICKING_UP

    def mark_delivering(self):
        """Mark the order as picked up and out for delivery."""
        self.status = STATUS_DELIVERING

    def complete(self, tick=None):
        """Mark the order as delivered and compute delivery metrics.

        Args:
            tick: Completion tick; defaults to the current simulated tick.
        """
        completion = _current_tick() if tick is None else tick
        self.completion_time = completion
        self.time_taken = max(completion - self.start_time, 0)
        self.efficiency = round(self.distance / max(self.time_taken, 1), 3)
        self.status = STATUS_COMPLETED

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "start_time": self.start_time,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
