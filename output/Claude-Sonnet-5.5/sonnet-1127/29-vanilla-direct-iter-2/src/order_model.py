"""Order model."""
import globalvar

_counter = [0]


def to_center(v):
    """Convert coordinate to grid cell center."""
    v = max(0, min(int(v), 799))
    return (v // 100) * 100 + 50


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        _counter[0] += 1
        self.id = _counter[0]
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0)
        self.finish_time = None

    def assign_to(self, rider_id):
        """Record assignment."""
        self.rider_id = rider_id
        self.status = "assigned"

    @property
    def distance(self):
        return abs(self.res_pos[0] - self.cus_pos[0]) + \
            abs(self.res_pos[1] - self.cus_pos[1])
