"""Order data model."""

import globalvar
from grid_map import to_grid_point
from path_planner import PathPlanner


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are automatically converted to grid cell centres.
    Status lifecycle: pending -> assigned -> picking_up -> delivering ->
    completed (or "unassigned" when no rider could be found).
    """

    _id_counter = 0

    def __init__(self, res_pos, cus_pos):
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("Positions must be (x, y) pairs")
        Order._id_counter += 1
        self.id = Order._id_counter
        self.raw_res = (int(res_pos[0]), int(res_pos[1]))
        self.raw_cus = (int(cus_pos[0]), int(cus_pos[1]))
        self.res_pos = to_grid_point(self.raw_res)
        self.cus_pos = to_grid_point(self.raw_cus)
        self.status = "pending"
        self.rider_id = None
        self.start_time = int(globalvar.get_value("tick", 0) or 0)
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.distance = PathPlanner().distance(self.res_pos, self.cus_pos)

    @classmethod
    def reset_counter(cls, value=0):
        """Reset the order id counter."""
        cls._id_counter = int(value)

    @property
    def res_x(self):
        return self.res_pos[0]

    @property
    def res_y(self):
        return self.res_pos[1]

    @property
    def cus_x(self):
        return self.cus_pos[0]

    @property
    def cus_y(self):
        return self.cus_pos[1]

    @property
    def completed(self):
        return self.status == "completed"

    def assign_to(self, rider_id):
        """Mark the order as assigned to ``rider_id``."""
        self.rider_id = rider_id
        if self.status in ("pending", "unassigned"):
            self.status = "assigned"
        self.assign_time = int(globalvar.get_value("tick", 0) or 0)

    def efficiency(self):
        """Delivery distance per tick, or None if not completed."""
        if not self.time_taken:
            return None
        return round(self.distance / self.time_taken, 2)

    def to_dict(self):
        """Serialisable representation."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "raw_restaurant": list(self.raw_res),
            "raw_customer": list(self.raw_cus),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self):
        return "Order(#%d %s->%s %s)" % (self.id, self.res_pos,
                                         self.cus_pos, self.status)
