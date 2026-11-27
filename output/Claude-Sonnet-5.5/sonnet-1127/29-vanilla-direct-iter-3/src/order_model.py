"""Order data model."""
import itertools

_counter = itertools.count(1)


def to_center(v):
    """Convert a coordinate to its grid cell center."""
    v = max(0, min(800, int(v)))
    cell = min(v // 100, 7)
    return cell * 100 + 50


class Order:
    """A delivery order; positions are converted to grid cell centers."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_counter)
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = 0
        self.end_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Assign this order to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def to_dict(self):
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "end_time": self.end_time, "distance": self.distance}
