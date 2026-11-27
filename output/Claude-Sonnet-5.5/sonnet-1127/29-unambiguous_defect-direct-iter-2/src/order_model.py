"""Order data model."""
import itertools

import globalvar

_ids = itertools.count(1)


def to_center(v):
    """Convert coordinate to grid cell centre."""
    v = max(0, min(799, int(v)))
    return (v // 100) * 100 + 50


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_ids)
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.create_time = globalvar.get_value("time", 0)
        self.complete_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Mark order assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self):
        """Mark order complete."""
        self.status = "completed"
        self.complete_time = globalvar.get_value("time", 0)

    @property
    def duration(self):
        """Ticks taken, or None."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.create_time

    def to_dict(self):
        """Serialise."""
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "create_time": self.create_time,
                "complete_time": self.complete_time,
                "distance": self.distance}
