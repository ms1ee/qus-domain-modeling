"""Order data model."""

import globalvar
from path_planner import to_grid_center, PathPlanner


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are automatically converted to grid cell centres.
    Status lifecycle: pending -> assigned -> picking_up -> delivering
    -> completed.
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        self.id = Order._next_id
        Order._next_id += 1
        self.raw_res_pos = (int(res_pos[0]), int(res_pos[1]))
        self.raw_cus_pos = (int(cus_pos[0]), int(cus_pos[1]))
        self.res_pos = (to_grid_center(res_pos[0]), to_grid_center(res_pos[1]))
        self.cus_pos = (to_grid_center(cus_pos[0]), to_grid_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.created_time = globalvar.get_value("time", 0)
        self.assigned_time = None
        self.accepted_time = None
        self.picked_time = None
        self.completed_time = None
        self.distance = 0

    @property
    def order_id(self):
        """Alias of ``id``."""
        return self.id

    def assign_to(self, rider_id):
        """Record that this order is assigned to rider ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assigned_time = globalvar.get_value("time", 0)

    def is_completed(self):
        """Return True if the order has been delivered."""
        return self.status == "completed"

    def direct_distance(self):
        """Manhattan distance from restaurant to customer."""
        return PathPlanner.manhattan(self.res_pos, self.cus_pos)

    def time_taken(self):
        """Ticks from creation to completion (None if not completed)."""
        if self.completed_time is None:
            return None
        return self.completed_time - self.created_time

    def to_dict(self):
        """Serialise the order to a JSON compatible dict."""
        return {
            "id": self.id,
            "raw_res_pos": list(self.raw_res_pos),
            "raw_cus_pos": list(self.raw_cus_pos),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_time": self.created_time,
            "assigned_time": self.assigned_time,
            "accepted_time": self.accepted_time,
            "picked_time": self.picked_time,
            "completed_time": self.completed_time,
            "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from a dict produced by ``to_dict``."""
        order = cls.__new__(cls)
        order.id = int(data["id"])
        order.raw_res_pos = tuple(data.get("raw_res_pos", data["res_pos"]))
        order.raw_cus_pos = tuple(data.get("raw_cus_pos", data["cus_pos"]))
        order.res_pos = tuple(data["res_pos"])
        order.cus_pos = tuple(data["cus_pos"])
        order.status = data.get("status", "pending")
        order.rider_id = data.get("rider_id")
        order.created_time = data.get("created_time", 0)
        order.assigned_time = data.get("assigned_time")
        order.accepted_time = data.get("accepted_time")
        order.picked_time = data.get("picked_time")
        order.completed_time = data.get("completed_time")
        order.distance = data.get("distance", 0)
        if cls._next_id <= order.id:
            cls._next_id = order.id + 1
        return order

    def __repr__(self):
        return "Order(id=%d, res=%s, cus=%s, status=%s, rider=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status, self.rider_id)
