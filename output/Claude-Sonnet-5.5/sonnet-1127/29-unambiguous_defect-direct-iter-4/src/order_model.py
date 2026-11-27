"""Order model."""
import itertools
import globalvar
from path_planner import center_pos, PathPlanner

_counter = itertools.count(1)


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_counter)
        self.res_pos = center_pos(*res_pos)
        self.cus_pos = center_pos(*cus_pos)
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0)
        self.complete_time = None
        self.duration = None
        self.distance = PathPlanner.distance(self.res_pos, self.cus_pos)

    def assign_to(self, rider_id):
        """Mark order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def to_dict(self):
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "complete_time": self.complete_time,
                "distance": self.distance}
