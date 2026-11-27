"""Order data model."""

import globalvar as gv
from path_planner import PathPlanner


class Order:
    """A delivery order from a restaurant to a customer.

    Attributes:
        id: unique order id.
        res_pos: (x, y) restaurant position.
        cus_pos: (x, y) customer position.
        status: "pending", "assigned", "picking_up", "delivering",
            "completed".
        rider_id: id of the assigned rider or None.
        start_time, assigned_time, pickup_time, complete_time: tick times.
        distance: Manhattan route length restaurant -> customer.
    """

    def __init__(self, res_pos, cus_pos):
        counter = gv.get_value("order_id_counter", 0) or 0
        counter += 1
        gv.set_value("order_id_counter", counter)
        self.id = counter
        self.res_pos = (int(res_pos[0]), int(res_pos[1]))
        self.cus_pos = (int(cus_pos[0]), int(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = gv.get_value("time", 0)
        self.assigned_time = None
        self.pickup_time = None
        self.complete_time = None
        self.assign_distance = None
        self.distance = PathPlanner.path_length(
            PathPlanner.plan_route(self.res_pos, [self.cus_pos]))

    def assign_to(self, rider_id):
        """Assign this order to the rider with ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assigned_time = gv.get_value("time", 0)

    def mark_picking_up(self):
        """Rider accepted the order and heads to the restaurant."""
        self.status = "picking_up"

    def mark_picked_up(self):
        """Rider arrived at the restaurant."""
        self.status = "delivering"
        self.pickup_time = gv.get_value("time", 0)

    def mark_completed(self):
        """Rider delivered the order."""
        self.status = "completed"
        self.complete_time = gv.get_value("time", 0)

    @property
    def time_taken(self):
        """Ticks from creation to completion, or None if unfinished."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.start_time

    def as_list(self):
        """Return ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.res_pos[0], self.res_pos[1], self.cus_pos[0], self.cus_pos[1]]

    def to_dict(self):
        """Serialise to a JSON-friendly dict."""
        return {
            "id": self.id, "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos), "status": self.status,
            "rider_id": self.rider_id, "start_time": self.start_time,
            "assigned_time": self.assigned_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "assign_distance": self.assign_distance,
            "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from :meth:`to_dict` output."""
        obj = cls.__new__(cls)
        obj.id = int(data["id"])
        obj.res_pos = tuple(data["res_pos"])
        obj.cus_pos = tuple(data["cus_pos"])
        obj.status = data.get("status", "pending")
        obj.rider_id = data.get("rider_id")
        obj.start_time = data.get("start_time", 0)
        obj.assigned_time = data.get("assigned_time")
        obj.pickup_time = data.get("pickup_time")
        obj.complete_time = data.get("complete_time")
        obj.assign_distance = data.get("assign_distance")
        obj.distance = data.get("distance", 0)
        return obj

    def __repr__(self):
        return "Order(id=%d, res=%s, cus=%s, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
