"""Order data model."""
import itertools

_counter = itertools.count(1)


def to_center(v):
    """Convert a coordinate to its grid cell center."""
    v = max(0, min(800, int(v)))
    c = (v // 100) * 100 + 50
    return min(c, 750)


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos, start_time=0):
        self.id = next(_counter)
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = start_time
        self.completion_time = None
        dx = self.res_pos[0] - self.cus_pos[0]
        dy = self.res_pos[1] - self.cus_pos[1]
        self.distance = (dx * dx + dy * dy) ** 0.5

    def assign_to(self, rider_id):
        """Assign this order to a rider id."""
        self.rider_id = rider_id
        self.status = "assigned"
