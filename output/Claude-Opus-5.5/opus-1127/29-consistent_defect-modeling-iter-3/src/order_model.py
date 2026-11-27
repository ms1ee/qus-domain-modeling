"""Order data model."""

import globalvar
from gridmap import to_grid_point


class Order:
    """A delivery order from a restaurant to a customer."""

    _id_counter = 0

    def __init__(self, res_pos, cus_pos, order_id=None):
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("positions must be (x, y) pairs")
        if order_id is None:
            Order._id_counter += 1
            order_id = Order._id_counter
        else:
            Order._id_counter = max(Order._id_counter, int(order_id))
        self.id = order_id
        self.raw_res_pos = [int(res_pos[0]), int(res_pos[1])]
        self.raw_cus_pos = [int(cus_pos[0]), int(cus_pos[1])]
        self.res_pos = to_grid_point(self.raw_res_pos)
        self.cus_pos = to_grid_point(self.raw_cus_pos)
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0) or 0
        self.assigned_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.planned_distance = None
        self.distance = abs(self.res_pos[0] - self.cus_pos[0]) + \
            abs(self.res_pos[1] - self.cus_pos[1])

    @property
    def restaurant_x(self):
        return self.res_pos[0]

    @property
    def restaurant_y(self):
        return self.res_pos[1]

    @property
    def customer_x(self):
        return self.cus_pos[0]

    @property
    def customer_y(self):
        return self.cus_pos[1]

    def assign_to(self, rider_id):
        """Record that this order is assigned to ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assigned_time = globalvar.get_value("tick", 0) or 0

    @property
    def efficiency(self):
        """Distance per tick for completed orders."""
        if self.time_taken:
            return self.distance / float(self.time_taken)
        return None

    def to_dict(self):
        return {
            "id": self.id, "raw_res_pos": self.raw_res_pos,
            "raw_cus_pos": self.raw_cus_pos, "res_pos": self.res_pos,
            "cus_pos": self.cus_pos, "status": self.status,
            "rider_id": self.rider_id, "start_time": self.start_time,
            "assigned_time": self.assigned_time, "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken, "distance": self.distance,
            "planned_distance": self.planned_distance,
        }

    @classmethod
    def from_dict(cls, data):
        o = cls(data["raw_res_pos"], data["raw_cus_pos"], order_id=data["id"])
        for key in ("status", "rider_id", "start_time", "assigned_time",
                    "pickup_time", "completion_time", "time_taken",
                    "distance", "planned_distance"):
            if key in data:
                setattr(o, key, data[key])
        return o

    def __repr__(self):
        return "Order(id=%s, res=%s, cus=%s, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
