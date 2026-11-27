"""Order data model."""
import itertools

from src import globalvar

_counter = itertools.count(1)


def to_grid(v):
    """Convert coordinate to top-left corner of its grid cell."""
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
        self.start_time = globalvar.get_value("time", 0) or 0
        self.end_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Record the rider this order is assigned to."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"

    def to_list(self):
        """Return [rx, ry, cx, cy]."""
        return [self.res_pos[0], self.res_pos[1],
                self.cus_pos[0], self.cus_pos[1]]
