"""Order data model."""
import itertools

from . import globalvar
from .pathplanner import center, PathPlanner

_ids = itertools.count(1)


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_ids)
        self.raw = [int(res_pos[0]), int(res_pos[1]),
                    int(cus_pos[0]), int(cus_pos[1])]
        self.res_pos = (center(res_pos[0]), center(res_pos[1]))
        self.cus_pos = (center(cus_pos[0]), center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0) or 0
        self.end_time = None
        self.distance = PathPlanner.distance(self.res_pos, self.cus_pos)

    def assign_to(self, rider_id):
        """Assign to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self):
        """Mark as completed."""
        self.status = "completed"
        self.end_time = globalvar.get_value("time", 0) or 0

    @property
    def duration(self):
        """Ticks taken, or None if unfinished."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    def to_dict(self):
        """Serialise."""
        return {"id": self.id, "res": list(self.res_pos),
                "cus": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "end_time": self.end_time, "distance": self.distance}
