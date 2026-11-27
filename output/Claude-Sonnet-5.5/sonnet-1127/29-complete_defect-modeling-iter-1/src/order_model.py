"""Order data model."""
import itertools

import globalvar
from gridmap import GRID

_ids = itertools.count(1)


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_ids)
        self.res_pos = (GRID.center(res_pos[0]), GRID.center(res_pos[1]))
        self.cus_pos = (GRID.center(cus_pos[0]), GRID.center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0) or 0
        self.completion_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))
        self.time_taken = None

    def assign_to(self, rider_id):
        """Assign this order to a rider id."""
        self.rider_id = rider_id
        self.status = "assigned"

    def to_dict(self):
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "completion_time": self.completion_time,
                "distance": self.distance, "time_taken": self.time_taken}
