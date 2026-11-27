"""Order data model."""
import globalvar

_counter = [0]


def to_center(v):
    """Convert coordinate to grid cell centre."""
    v = max(0, min(800, int(v)))
    if v == 800:
        v = 799
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
        self.end_time = None
        dx = self.res_pos[0] - self.cus_pos[0]
        dy = self.res_pos[1] - self.cus_pos[1]
        self.distance = (dx * dx + dy * dy) ** 0.5

    def assign_to(self, rider_id):
        """Assign to a rider."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"

    def complete(self, t):
        """Mark completed."""
        self.status = "completed"
        self.end_time = t

    def to_dict(self):
        return {"id": self.id, "res": list(self.res_pos),
                "cus": list(self.cus_pos), "status": self.status,
                "rider": self.rider_id, "start": self.start_time,
                "end": self.end_time, "distance": self.distance}
