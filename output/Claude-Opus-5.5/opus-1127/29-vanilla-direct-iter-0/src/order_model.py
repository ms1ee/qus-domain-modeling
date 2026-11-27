"""Order data model."""

import globalvar


def _next_order_id():
    counter = globalvar.get_value("order_id_counter", 0) or 0
    counter += 1
    globalvar.set_value("order_id_counter", counter)
    return counter


class Order:
    """A delivery order from a restaurant to a customer.

    Attributes:
        id: unique order id.
        res_pos: (x, y) restaurant position.
        cus_pos: (x, y) customer position.
        status: "pending", "assigned", "picking_up", "delivering", "completed".
        rider_id: id of the assigned rider or None.
    """

    def __init__(self, res_pos, cus_pos):
        self.id = _next_order_id()
        self.res_pos = (int(res_pos[0]), int(res_pos[1]))
        self.cus_pos = (int(cus_pos[0]), int(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.created_time = globalvar.get_value("time", 0) or 0
        self.assign_time = None
        self.pickup_time = None
        self.complete_time = None
        self.distance = None
        self.estimated_time = None

    def assign_to(self, rider_id):
        """Record the assignment of this order to rider ``rider_id``."""
        self.rider_id = rider_id
        self.status = "assigned"
        self.assign_time = globalvar.get_value("time", 0) or 0

    @property
    def time_taken(self):
        """Ticks from creation to completion, or None if not completed."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.created_time

    def to_dict(self):
        """Serialize the order to a dict."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_time": self.created_time,
            "assign_time": self.assign_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
            "estimated_time": self.estimated_time,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from a dict without consuming a new id."""
        obj = cls.__new__(cls)
        obj.id = data["id"]
        obj.res_pos = tuple(data["res_pos"])
        obj.cus_pos = tuple(data["cus_pos"])
        obj.status = data.get("status", "pending")
        obj.rider_id = data.get("rider_id")
        obj.created_time = data.get("created_time", 0)
        obj.assign_time = data.get("assign_time")
        obj.pickup_time = data.get("pickup_time")
        obj.complete_time = data.get("complete_time")
        obj.distance = data.get("distance")
        obj.estimated_time = data.get("estimated_time")
        return obj

    def __repr__(self):
        return "Order(id=%s, res=%s, cus=%s, status=%s, rider=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status, self.rider_id)
