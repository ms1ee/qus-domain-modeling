"""Order model."""
import itertools
import globalvar
from pathplanner import GridMap

_ids = itertools.count(1)
_grid = GridMap()


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_ids)
        self.res_pos = (_grid.center(res_pos[0]), _grid.center(res_pos[1]))
        self.cus_pos = (_grid.center(cus_pos[0]), _grid.center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0) or 0
        self.completion_time = None
        self.time_taken = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Assign to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, tick):
        """Mark completed."""
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = tick - self.start_time

    def to_dict(self):
        """Serializable form."""
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "completion_time": self.completion_time,
                "distance": self.distance, "time_taken": self.time_taken}
