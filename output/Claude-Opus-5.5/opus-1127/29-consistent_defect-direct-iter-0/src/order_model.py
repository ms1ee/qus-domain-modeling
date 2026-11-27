"""Order data model."""

import itertools

import globalvar
from config import CELL_SIZE, GRID_DIM

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"

_id_counter = itertools.count(1)


def reset_order_ids(start=1):
    """Reset the order ID counter (used when loading state)."""
    global _id_counter
    _id_counter = itertools.count(start)


def _grid_index(value):
    """Return the clamped grid cell index (0..GRID_DIM-1) for a coordinate."""
    idx = int(value) // CELL_SIZE
    return max(0, min(GRID_DIM - 1, idx))


def to_grid_cell(value):
    """Convert a coordinate to the top-left corner of its grid cell."""
    return _grid_index(value) * CELL_SIZE


def to_grid_center(value):
    """Convert a coordinate to its grid cell center: (v // 100) * 100 + 50."""
    return _grid_index(value) * CELL_SIZE + CELL_SIZE // 2


def _now():
    t = globalvar.get_value("time")
    return t if isinstance(t, int) else 0


def _parse_pos(pos, name):
    try:
        x, y = pos
        return int(x), int(y)
    except (TypeError, ValueError):
        raise ValueError("%s must be a pair of integers, got %r" % (name, pos))


class Order:
    """A delivery order from a restaurant to a customer.

    Attributes:
        id: unique order ID.
        status: one of pending/assigned/picking_up/delivering/completed.
        raw_res_pos / raw_cus_pos: coordinates as entered.
        res_pos / cus_pos: converted grid-cell center coordinates.
        res_cell / cus_cell: top-left corner of the grid cells.
        rider_id: ID of the assigned rider (None if unassigned).
    """

    def __init__(self, res_pos, cus_pos, order_id=None):
        rx, ry = _parse_pos(res_pos, "res_pos")
        cx, cy = _parse_pos(cus_pos, "cus_pos")
        self.id = order_id if order_id is not None else next(_id_counter)
        self.raw_res_pos = (rx, ry)
        self.raw_cus_pos = (cx, cy)
        self.res_pos = (to_grid_center(rx), to_grid_center(ry))
        self.cus_pos = (to_grid_center(cx), to_grid_center(cy))
        self.res_cell = (to_grid_cell(rx), to_grid_cell(ry))
        self.cus_cell = (to_grid_cell(cx), to_grid_cell(cy))
        self.status = STATUS_PENDING
        self.rider_id = None
        self.created_time = _now()
        self.assigned_time = None
        self.accepted_time = None
        self.pickup_time = None
        self.completed_time = None
        self.travel_distance = 0

    @property
    def distance(self):
        """Manhattan distance between restaurant and customer."""
        return (abs(self.res_pos[0] - self.cus_pos[0])
                + abs(self.res_pos[1] - self.cus_pos[1]))

    @property
    def time_taken(self):
        """Ticks from creation to completion, or None if not completed."""
        if self.completed_time is None:
            return None
        return self.completed_time - self.created_time

    def assign_to(self, rider_id):
        """Record that this order is assigned to ``rider_id``."""
        self.rider_id = rider_id
        if self.status == STATUS_PENDING:
            self.status = STATUS_ASSIGNED
        self.assigned_time = _now()

    def is_completed(self):
        """Return True if the order has been delivered."""
        return self.status == STATUS_COMPLETED

    def is_active(self):
        """Return True if the order is not yet delivered."""
        return not self.is_completed()

    def to_dict(self):
        """Serialise the order to a JSON-compatible dict."""
        return {
            "id": self.id,
            "raw_res_pos": list(self.raw_res_pos),
            "raw_cus_pos": list(self.raw_cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_time": self.created_time,
            "assigned_time": self.assigned_time,
            "accepted_time": self.accepted_time,
            "pickup_time": self.pickup_time,
            "completed_time": self.completed_time,
            "travel_distance": self.travel_distance,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from :meth:`to_dict` output."""
        order = cls(data["raw_res_pos"], data["raw_cus_pos"],
                    order_id=data["id"])
        for key in ("status", "rider_id", "created_time", "assigned_time",
                    "accepted_time", "pickup_time", "completed_time",
                    "travel_distance"):
            if key in data:
                setattr(order, key, data[key])
        return order

    def __repr__(self):
        return "Order(id=%s, res=%s, cus=%s, status=%s, rider=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status, self.rider_id)
