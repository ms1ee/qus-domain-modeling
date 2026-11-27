"""Order data model."""

import globalvar
from path_planner import PathPlanner, to_grid_center


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are converted to grid cell centres on creation.

    Attributes:
        id: unique order id.
        res_pos / cus_pos: (x, y) tuples of grid-cell centres.
        status: "pending", "assigned", "picking_up", "delivering", "completed".
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("Positions must be (x, y) pairs")
        self.raw = [res_pos[0], res_pos[1], cus_pos[0], cus_pos[1]]
        self.res_pos = (to_grid_center(res_pos[0]), to_grid_center(res_pos[1]))
        self.cus_pos = (to_grid_center(cus_pos[0]), to_grid_center(cus_pos[1]))
        self.id = Order._next_id
        Order._next_id += 1
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0)
        self.assign_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.distance = PathPlanner.path_length(
            [self.res_pos] + PathPlanner.plan_route(self.res_pos, self.cus_pos))
        self.efficiency = None

    @classmethod
    def reset_ids(cls, start=1):
        """Reset the id counter (used on system initialisation)."""
        cls._next_id = start

    @property
    def order_id(self):
        """Alias for ``id``."""
        return self.id

    @property
    def is_completed(self):
        """True once the order has been delivered."""
        return self.status == "completed"

    def as_list(self):
        """Return ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.res_pos[0], self.res_pos[1], self.cus_pos[0], self.cus_pos[1]]

    def assign_to(self, rider_id):
        """Mark the order as assigned to ``rider_id``."""
        self.rider_id = rider_id
        self.status = "assigned"
        self.assign_time = globalvar.get_value("tick", 0)

    def mark_picked_up(self):
        """Record that the rider reached the restaurant."""
        self.status = "delivering"
        self.pickup_time = globalvar.get_value("tick", 0)

    def mark_completed(self):
        """Record delivery completion and efficiency data."""
        self.status = "completed"
        self.completion_time = globalvar.get_value("tick", 0)
        self.time_taken = self.completion_time - (self.start_time or 0)
        if self.time_taken and self.time_taken > 0:
            self.efficiency = round(self.distance / float(self.time_taken), 2)
        else:
            self.efficiency = None

    def to_dict(self):
        """Serialise the order to a dictionary."""
        return {
            "id": self.id, "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos), "status": self.status,
            "rider_id": self.rider_id, "start_time": self.start_time,
            "assign_time": self.assign_time, "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken, "distance": self.distance,
            "efficiency": self.efficiency,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from ``to_dict`` output (id counter untouched)."""
        saved_next = cls._next_id
        o = cls(tuple(data["res_pos"]), tuple(data["cus_pos"]))
        cls._next_id = saved_next
        for key in ("id", "status", "rider_id", "start_time", "assign_time",
                    "pickup_time", "completion_time", "time_taken",
                    "distance", "efficiency"):
            if key in data:
                setattr(o, key, data[key])
        return o

    def __repr__(self):
        return "Order(id=%d, res=%r, cus=%r, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
