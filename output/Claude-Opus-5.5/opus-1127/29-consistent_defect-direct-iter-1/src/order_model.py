"""Order data model."""

import itertools

import globalvar
from path_planner import PathPlanner

_id_counter = itertools.count(1)


class Order:
    """A single delivery order.

    Attributes:
        id: unique order id.
        res_pos / cus_pos: grid-converted restaurant / customer positions.
        status: "pending", "assigned", "picked_up" or "completed".
        rider_id: id of the assigned rider or None.
    """

    def __init__(self, res_pos, cus_pos):
        self.id = next(_id_counter)
        self.raw_res_pos = (int(res_pos[0]), int(res_pos[1]))
        self.raw_cus_pos = (int(cus_pos[0]), int(cus_pos[1]))
        self.res_pos = PathPlanner.to_grid(self.raw_res_pos)
        self.cus_pos = PathPlanner.to_grid(self.raw_cus_pos)
        self.status = "pending"
        self.rider_id = None
        self.created_time = globalvar.get_value("time", 0) or 0
        self.assigned_time = None
        self.picked_time = None
        self.completed_time = None

    def assign_to(self, rider_id):
        """Mark the order as assigned to ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assigned_time = globalvar.get_value("time", 0) or 0

    @property
    def distance(self):
        """Street distance from restaurant to customer."""
        return PathPlanner.manhattan(self.res_pos, self.cus_pos)

    @property
    def time_taken(self):
        """Ticks from creation to completion, or None if not completed."""
        if self.completed_time is None:
            return None
        return self.completed_time - self.created_time

    def to_dict(self):
        """Serialize to a JSON compatible dict."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_time": self.created_time,
            "assigned_time": self.assigned_time,
            "picked_time": self.picked_time,
            "completed_time": self.completed_time,
            "distance": self.distance,
        }

    def __repr__(self):
        return "Order(id=%d, %s->%s, %s)" % (self.id, self.res_pos,
                                             self.cus_pos, self.status)
