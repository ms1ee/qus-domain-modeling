"""Order data model."""
import itertools

import globalvar

_counter = itertools.count(1)


def to_grid(v):
    """Convert coordinate to top-left corner of its grid cell (0-700)."""
    v = int(v)
    return max(0, min(700, (v // 100) * 100))


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_counter)
        self.res_pos = (to_grid(res_pos[0]), to_grid(res_pos[1]))
        self.cus_pos = (to_grid(cus_pos[0]), to_grid(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0)
        self.end_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Mark order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def to_dict(self):
        return {"id": self.id, "res": list(self.res_pos),
                "cus": list(self.cus_pos), "status": self.status,
                "rider": self.rider_id, "start": self.start_time,
                "end": self.end_time, "distance": self.distance}
