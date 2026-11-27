"""Order data model."""
import globalvar

_counter = [0]


def to_center(v):
    """Convert a coordinate to its grid cell center."""
    v = max(0, min(int(v), 799))
    return (v // 100) * 100 + 50


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        _counter[0] += 1
        self.id = _counter[0]
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.start_time = globalvar.get_value("time", 0) or 0
        self.completion_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))
        self.time_taken = None
        self.rider_id = None
        self.status = "pending"

    def assign_to(self, rider_id):
        """Assign to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"
