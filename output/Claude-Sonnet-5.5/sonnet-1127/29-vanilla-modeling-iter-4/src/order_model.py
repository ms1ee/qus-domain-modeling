"""Order data model."""
import itertools

import globalvar
from grid_map import GridMap

_counter = itertools.count(1)


class Order:
    """A delivery order. Positions are converted to grid cell centers."""

    def __init__(self, res_pos, cus_pos):
        g = GridMap()
        self.id = next(_counter)
        self.res_pos = g.center_of(res_pos[0], res_pos[1])
        self.cus_pos = g.center_of(cus_pos[0], cus_pos[1])
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0) or 0
        self.completion_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))
        self.time_taken = None

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, tick):
        self.completion_time = tick
        self.time_taken = tick - self.start_time
        self.status = "completed"

    def to_dict(self):
        return {"id": self.id, "restaurant": list(self.res_pos),
                "customer": list(self.cus_pos), "start_time": self.start_time,
                "completion_time": self.completion_time,
                "distance": self.distance, "time_taken": self.time_taken,
                "rider_id": self.rider_id, "status": self.status}
