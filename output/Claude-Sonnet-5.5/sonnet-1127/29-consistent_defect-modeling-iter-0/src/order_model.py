"""Order data model."""
import itertools

import globalvar

_ids = itertools.count(1)


def to_grid(v):
    """Convert a coordinate to the top-left corner of its grid cell."""
    v = int(v)
    return max(0, min(700, (v // 100) * 100))


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_ids)
        self.res_pos = (to_grid(res_pos[0]), to_grid(res_pos[1]))
        self.cus_pos = (to_grid(cus_pos[0]), to_grid(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0) or 0
        self.completion_time = None
        self.distance = float(
            abs(self.res_pos[0] - self.cus_pos[0])
            + abs(self.res_pos[1] - self.cus_pos[1]))

    @property
    def time_taken(self):
        if self.completion_time is None:
            return None
        return self.completion_time - self.start_time

    def assign_to(self, rider_id):
        """Assign this order to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"
