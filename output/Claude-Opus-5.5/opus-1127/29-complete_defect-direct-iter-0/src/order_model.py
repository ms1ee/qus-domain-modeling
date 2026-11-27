"""Order data model."""

import globalvar
from path_planner import PathPlanner


class Order:
    """A delivery order from a restaurant to a customer.

    Input coordinates (0-800) are converted to grid-cell centres.
    Status lifecycle: pending -> assigned -> picking_up -> delivering ->
    completed.
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        self.id = Order._next_id
        Order._next_id += 1
        self.raw_res_pos = (int(res_pos[0]), int(res_pos[1]))
        self.raw_cus_pos = (int(cus_pos[0]), int(cus_pos[1]))
        self.res_pos = PathPlanner.point_to_center(self.raw_res_pos)
        self.cus_pos = PathPlanner.point_to_center(self.raw_cus_pos)
        self.res_grid = (PathPlanner.to_grid_index(self.raw_res_pos[0]),
                         PathPlanner.to_grid_index(self.raw_res_pos[1]))
        self.cus_grid = (PathPlanner.to_grid_index(self.raw_cus_pos[0]),
                         PathPlanner.to_grid_index(self.raw_cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.create_time = globalvar.get_value("time", 0) or 0
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.time_taken = None
        self.trip_distance = PathPlanner.path_length(
            self.res_pos, PathPlanner.find_path(self.res_pos, self.cus_pos))
        self.distance = None
        self.efficiency = None

    @classmethod
    def reset_counter(cls):
        """Reset the order id counter."""
        cls._next_id = 1

    def assign_to(self, rider_id):
        """Record that this order is assigned to ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assign_time = globalvar.get_value("time", 0) or 0

    def is_completed(self):
        """Return True if delivered."""
        return self.status == "completed"

    def to_dict(self):
        """Serialisable representation."""
        return {
            "id": self.id,
            "raw_res_pos": list(self.raw_res_pos),
            "raw_cus_pos": list(self.raw_cus_pos),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "create_time": self.create_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "efficiency": self.efficiency,
        }

    def __repr__(self):
        return "Order(id=%d, %s->%s, %s)" % (self.id, self.res_pos,
                                            self.cus_pos, self.status)
