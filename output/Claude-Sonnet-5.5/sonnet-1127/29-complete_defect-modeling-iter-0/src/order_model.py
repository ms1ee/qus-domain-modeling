"""Order data model."""
import itertools

import globalvar
from pathplanner import GridMap, PathPlanner

_ids = itertools.count(1)


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_ids)
        self.res_pos = (GridMap.center(res_pos[0]), GridMap.center(res_pos[1]))
        self.cus_pos = (GridMap.center(cus_pos[0]), GridMap.center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0) or 0
        self.completion_time = None
        self.distance = PathPlanner.distance(self.res_pos, self.cus_pos)
        self.time_taken = None

    def assign_to(self, rider_id):
        """Record the rider this order is assigned to."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, tick):
        """Mark as completed."""
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = tick - self.start_time
