"""Order data model."""

import globalvar
from path_planner import to_grid_center, PathPlanner


def _now():
    t = globalvar.get_value("time")
    return t if isinstance(t, int) else 0


class Order:
    """A delivery order from a restaurant to a customer.

    Attributes:
        id: unique order id.
        res_pos: (x, y) restaurant location (grid cell centre).
        cus_pos: (x, y) customer location (grid cell centre).
        status: "pending", "assigned", "picking_up", "delivering",
            "completed".
        rider_id: id of assigned rider or None.
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        self.id = Order._next_id
        Order._next_id += 1
        self.raw_res = (int(res_pos[0]), int(res_pos[1]))
        self.raw_cus = (int(cus_pos[0]), int(cus_pos[1]))
        self.res_pos = (to_grid_center(res_pos[0]), to_grid_center(res_pos[1]))
        self.cus_pos = (to_grid_center(cus_pos[0]), to_grid_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = _now()
        self.assign_time = None
        self.pickup_time = None
        self.complete_time = None
        self.distance = PathPlanner.manhattan(self.res_pos, self.cus_pos)

    def assign_to(self, rider_id):
        """Record assignment of this order to rider ``rider_id``."""
        self.rider_id = rider_id
        self.assign_time = _now()
        if self.status == "pending":
            self.status = "assigned"

    @property
    def time_taken(self):
        """Ticks from creation to completion (None if not completed)."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.start_time

    def to_dict(self):
        """Serialise to a JSON friendly dict."""
        return {
            "id": self.id,
            "raw_res": list(self.raw_res),
            "raw_cus": list(self.raw_cus),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "assign_time": self.assign_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from ``to_dict`` output."""
        order = cls(data["res_pos"], data["cus_pos"])
        order.id = data["id"]
        order.raw_res = tuple(data.get("raw_res", data["res_pos"]))
        order.raw_cus = tuple(data.get("raw_cus", data["cus_pos"]))
        order.res_pos = tuple(data["res_pos"])
        order.cus_pos = tuple(data["cus_pos"])
        order.status = data["status"]
        order.rider_id = data["rider_id"]
        order.start_time = data["start_time"]
        order.assign_time = data.get("assign_time")
        order.pickup_time = data.get("pickup_time")
        order.complete_time = data.get("complete_time")
        order.distance = data.get("distance", order.distance)
        cls._next_id = max(cls._next_id, order.id + 1)
        return order

    def __repr__(self):
        return "Order(id=%d, res=%s, cus=%s, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
