"""Order data model."""

import globalvar
from path_planner import PathPlanner

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _now():
    t = globalvar.get_value("time")
    return t if isinstance(t, int) else 0


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are converted to the centre of their grid cell.

    Attributes:
        id: unique auto-incrementing order id.
        res_pos: (x, y) restaurant position (grid centre).
        cus_pos: (x, y) customer position (grid centre).
        status: "pending", "assigned", "picking_up", "delivering" or
            "completed".
        rider_id: id of the assigned rider or None.
        created_time / assigned_time / pickup_time / completed_time: ticks.
        distance: street distance restaurant -> customer.
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        self.id = Order._next_id
        Order._next_id += 1
        self.raw = [int(res_pos[0]), int(res_pos[1]),
                    int(cus_pos[0]), int(cus_pos[1])]
        self.res_pos = PathPlanner.to_grid_center(res_pos)
        self.cus_pos = PathPlanner.to_grid_center(cus_pos)
        self.status = STATUS_PENDING
        self.rider_id = None
        self.created_time = _now()
        self.assigned_time = None
        self.accepted_time = None
        self.pickup_time = None
        self.completed_time = None
        self.distance = PathPlanner.manhattan(self.res_pos, self.cus_pos)
        self.travel_distance = 0

    @classmethod
    def reset_counter(cls, value=1):
        """Reset the id counter (used when the system is reinitialised)."""
        cls._next_id = value

    def assign_to(self, rider_id):
        """Record that this order is assigned to ``rider_id``."""
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED
        self.assigned_time = _now()

    @property
    def time_taken(self):
        """Ticks from creation to completion, or None while open."""
        if self.completed_time is None:
            return None
        return self.completed_time - self.created_time

    @property
    def efficiency(self):
        """Delivery distance per tick taken (None while open)."""
        tt = self.time_taken
        if not tt:
            return None
        return round(self.distance / tt, 2)

    def is_completed(self):
        """True when the order has been delivered."""
        return self.status == STATUS_COMPLETED

    def to_list(self):
        """Return [restaurant_x, restaurant_y, customer_x, customer_y]."""
        return [self.res_pos[0], self.res_pos[1],
                self.cus_pos[0], self.cus_pos[1]]

    def to_dict(self):
        """Serialise the order to a JSON friendly dictionary."""
        return {
            "id": self.id,
            "raw": self.raw,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_time": self.created_time,
            "assigned_time": self.assigned_time,
            "accepted_time": self.accepted_time,
            "pickup_time": self.pickup_time,
            "completed_time": self.completed_time,
            "distance": self.distance,
            "travel_distance": self.travel_distance,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from :meth:`to_dict` output."""
        order = cls(data["res_pos"], data["cus_pos"])
        order.id = int(data["id"])
        order.raw = list(data.get("raw", order.raw))
        order.status = data.get("status", STATUS_PENDING)
        order.rider_id = data.get("rider_id")
        for key in ("created_time", "assigned_time", "accepted_time",
                    "pickup_time", "completed_time", "travel_distance"):
            if key in data:
                setattr(order, key, data[key])
        if order.created_time is None:
            order.created_time = 0
        return order

    def __repr__(self):
        return ("Order(id=%d, res=%s, cus=%s, status=%s, rider=%s)"
                % (self.id, self.res_pos, self.cus_pos, self.status,
                   self.rider_id))
