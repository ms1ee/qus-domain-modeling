"""Order data model."""

import itertools

import globalvar

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _pos_tuple(pos):
    """Return ``pos`` as an ``(int, int)`` tuple."""
    return int(pos[0]), int(pos[1])


class Order:
    """A delivery order from a restaurant to a customer.

    Attributes:
        id: unique auto-incremented order id.
        res_pos: restaurant position.
        cus_pos: customer position.
        status: one of pending/assigned/picking_up/delivering/completed.
        rider_id: id of the assigned rider (or None).
    """

    _id_counter = itertools.count(1)

    def __init__(self, res_pos, cus_pos):
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("Positions must contain exactly two coordinates")
        self.id = next(Order._id_counter)
        self.res_pos = res_pos
        self.cus_pos = cus_pos
        self.status = STATUS_PENDING
        self.rider_id = None
        self.created_time = globalvar.get_value("current_time", 0) or 0
        self.assigned_time = None
        self.accepted_time = None
        self.pickup_time = None
        self.completed_time = None
        rx, ry = _pos_tuple(res_pos)
        cx, cy = _pos_tuple(cus_pos)
        self.distance = abs(rx - cx) + abs(ry - cy)

    def assign_to(self, rider_id):
        """Record the assignment of this order to ``rider_id``."""
        self.rider_id = rider_id
        if self.status == STATUS_PENDING:
            self.status = STATUS_ASSIGNED
        self.assigned_time = globalvar.get_value("current_time", 0) or 0

    @property
    def is_completed(self):
        """True once the order has been delivered."""
        return self.status == STATUS_COMPLETED

    @property
    def time_taken(self):
        """Ticks from creation to completion, or None if not completed."""
        if self.completed_time is None:
            return None
        return self.completed_time - self.created_time

    @property
    def efficiency(self):
        """Delivery efficiency: restaurant->customer distance per tick."""
        taken = self.time_taken
        if taken is None:
            return None
        if taken <= 0:
            return float(self.distance)
        return round(self.distance / taken, 2)

    def to_dict(self):
        """Serialise the order to a JSON compatible dict."""
        return {
            "id": self.id,
            "res_pos": list(_pos_tuple(self.res_pos)),
            "cus_pos": list(_pos_tuple(self.cus_pos)),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_time": self.created_time,
            "assigned_time": self.assigned_time,
            "accepted_time": self.accepted_time,
            "pickup_time": self.pickup_time,
            "completed_time": self.completed_time,
            "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from :meth:`to_dict` output."""
        order = cls(tuple(data["res_pos"]), tuple(data["cus_pos"]))
        order.id = int(data["id"])
        for key in ("status", "rider_id", "created_time", "assigned_time",
                    "accepted_time", "pickup_time", "completed_time"):
            if key in data:
                setattr(order, key, data[key])
        cls.bump_counter(order.id)
        return order

    @classmethod
    def bump_counter(cls, used_id):
        """Make sure future ids are greater than ``used_id``."""
        current = next(cls._id_counter)
        cls._id_counter = itertools.count(max(current, used_id + 1))

    def __repr__(self):
        return ("Order(id={}, res={}, cus={}, status={}, rider={})"
                .format(self.id, _pos_tuple(self.res_pos),
                        _pos_tuple(self.cus_pos), self.status, self.rider_id))
