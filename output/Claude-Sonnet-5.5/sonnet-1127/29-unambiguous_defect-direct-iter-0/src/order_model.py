"""Order model."""
import itertools

_counter = itertools.count(1)


def to_center(v):
    """Convert coordinate to grid cell center."""
    v = max(0, min(799, int(v)))
    return (v // 100) * 100 + 50


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        import globalvar
        self.id = next(_counter)
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0) or 0
        self.end_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Assign to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, now):
        """Mark completed."""
        self.status = "completed"
        self.end_time = now

    def to_dict(self):
        return {"id": self.id, "res": list(self.res_pos),
                "cus": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "end_time": self.end_time, "distance": self.distance}
