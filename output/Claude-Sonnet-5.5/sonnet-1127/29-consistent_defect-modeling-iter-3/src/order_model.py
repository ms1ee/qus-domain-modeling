"""Order data model."""
import itertools

import globalvar
from gridmap import GridMap

_counter = itertools.count(1)
_grid = GridMap()


def reset_counter():
    global _counter
    _counter = itertools.count(1)


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_counter)
        self.res_pos = _grid.to_cell_corner(*res_pos)
        self.cus_pos = _grid.to_cell_corner(*cus_pos)
        self.start_time = globalvar.get_value("tick", 0)
        self.completion_time = None
        self.rider_id = None
        self.status = "pending"
        self.distance = float(abs(self.res_pos[0] - self.cus_pos[0])
                              + abs(self.res_pos[1] - self.cus_pos[1]))
        self.time_taken = None

    def assign_to(self, rider_id):
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, tick):
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = tick - self.start_time

    def to_dict(self):
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "start_time": self.start_time,
                "completion_time": self.completion_time,
                "rider_id": self.rider_id, "status": self.status,
                "distance": self.distance, "time_taken": self.time_taken}
