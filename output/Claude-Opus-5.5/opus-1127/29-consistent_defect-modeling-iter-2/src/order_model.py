"""Order data model."""

import globalvar
from path_planner import GridMap, PathPlanner

_GRID = GridMap()
_PLANNER = PathPlanner()


def to_grid_point(pos):
    """Convert a raw (x, y) position into the centre of its grid cell."""
    if pos is None or len(pos) != 2:
        raise ValueError("position must contain exactly two coordinates")
    return (_GRID.to_cell_center(pos[0]), _GRID.to_cell_center(pos[1]))


class Order:
    """A delivery order from a restaurant to a customer.

    Attributes:
        id: unique order id.
        res_pos / cus_pos: grid-converted restaurant / customer positions.
        status: "pending", "assigned", "picking_up", "delivering",
            "completed".
    """

    def __init__(self, res_pos, cus_pos):
        new_id = (globalvar.get_value("order_id_counter", 0) or 0) + 1
        globalvar.set_value("order_id_counter", new_id)
        self.id = new_id
        self.raw = [int(res_pos[0]), int(res_pos[1]),
                    int(cus_pos[0]), int(cus_pos[1])]
        self.res_pos = to_grid_point(res_pos)
        self.cus_pos = to_grid_point(cus_pos)
        self.start_time = globalvar.get_value("tick", 0) or 0
        self.assigned_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.rider_id = None
        self.status = "pending"
        pts = _PLANNER.plan(*self.res_pos, *self.cus_pos)
        self.distance = _PLANNER.path_length(self.res_pos, pts)

    # Convenience accessors -------------------------------------------------
    @property
    def order_id(self):
        return self.id

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

    def as_list(self):
        """Return [restaurant_x, restaurant_y, customer_x, customer_y]."""
        return [self.res_pos[0], self.res_pos[1],
                self.cus_pos[0], self.cus_pos[1]]

    def is_completed(self):
        return self.status == "completed"

    # Lifecycle ------------------------------------------------------------
    def assign_to(self, rider_id):
        """Mark the order as assigned to ``rider_id``."""
        self.rider_id = rider_id
        self.assigned_time = globalvar.get_value("tick", 0) or 0
        if self.status == "pending":
            self.status = "assigned"

    def mark_completed(self, tick=None):
        """Mark the order completed and record timing data."""
        if tick is None:
            tick = globalvar.get_value("tick", 0) or 0
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = tick - self.start_time

    @property
    def efficiency(self):
        """Delivery distance per tick of total time (None if unfinished)."""
        if self.time_taken is None:
            return None
        return self.distance / self.time_taken if self.time_taken else float(self.distance)

    # Persistence ----------------------------------------------------------
    def to_dict(self):
        return {
            "id": self.id, "raw": self.raw,
            "res_pos": list(self.res_pos), "cus_pos": list(self.cus_pos),
            "start_time": self.start_time, "assigned_time": self.assigned_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken, "rider_id": self.rider_id,
            "status": self.status, "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls.__new__(cls)
        obj.id = int(data["id"])
        obj.raw = list(data.get("raw", []))
        obj.res_pos = tuple(data["res_pos"])
        obj.cus_pos = tuple(data["cus_pos"])
        obj.start_time = data.get("start_time", 0)
        obj.assigned_time = data.get("assigned_time")
        obj.pickup_time = data.get("pickup_time")
        obj.completion_time = data.get("completion_time")
        obj.time_taken = data.get("time_taken")
        obj.rider_id = data.get("rider_id")
        obj.status = data.get("status", "pending")
        obj.distance = data.get("distance", 0)
        return obj

    def __repr__(self):
        return (f"Order(id={self.id}, res={self.res_pos}, cus={self.cus_pos}, "
                f"status={self.status}, rider={self.rider_id})")
