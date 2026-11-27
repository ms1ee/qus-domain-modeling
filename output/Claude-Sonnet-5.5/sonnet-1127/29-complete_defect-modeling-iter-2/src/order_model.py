"""Order data model."""
import itertools
import globalvar

_counter = itertools.count(1)


def to_center(v):
    """Convert a coordinate to its grid cell center."""
    return min(max(int(v) // 100, 0), 7) * 100 + 50


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_counter)
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.start_time = globalvar.get_value("tick", 0)
        self.completion_time = None
        self.rider_id = None
        self.status = "pending"
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0]) +
                         abs(self.res_pos[1] - self.cus_pos[1]))

    @property
    def time_taken(self):
        if self.completion_time is None:
            return None
        return self.completion_time - self.start_time

    def assign_to(self, rider_id):
        """Mark order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"
