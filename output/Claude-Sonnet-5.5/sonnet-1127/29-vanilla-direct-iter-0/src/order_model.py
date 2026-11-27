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
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        _counter[0] += 1
        self.id = _counter[0]
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0) or 0
        self.end_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self):
        """Mark delivered."""
        self.status = "completed"
        self.end_time = globalvar.get_value("time", 0) or 0

    @property
    def duration(self):
        """Ticks taken, or None."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    def to_dict(self):
        """Serialise."""
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "end_time": self.end_time, "distance": self.distance}
