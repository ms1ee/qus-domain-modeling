"""Order data model."""
import itertools

from src import globalvar

_counter = itertools.count(1)


def to_center(v):
    """Convert coordinate to grid cell center."""
    v = max(0, min(800, int(v)))
    g = min(v // 100, 7)
    return g * 100 + 50


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_counter)
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0) or 0
        self.completed_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Assign order to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self):
        """Mark as completed."""
        self.status = "completed"
        self.completed_time = globalvar.get_value("time", 0) or 0

    @property
    def duration(self):
        """Time taken, or None if unfinished."""
        if self.completed_time is None:
            return None
        return self.completed_time - self.start_time

    def to_dict(self):
        """Serialise."""
        return {"id": self.id, "res": list(self.res_pos),
                "cus": list(self.cus_pos), "status": self.status,
                "rider": self.rider_id, "start": self.start_time,
                "duration": self.duration, "distance": self.distance}
