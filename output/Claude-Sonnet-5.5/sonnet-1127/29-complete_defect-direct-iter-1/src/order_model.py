"""Order data model."""

import globalvar
from path_planner import to_center, PathPlanner


class Order:
    """A delivery order."""

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        self.id = Order._next_id
        Order._next_id += 1
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0) or 0
        self.complete_time = None
        self.distance = PathPlanner.distance(self.res_pos, self.cus_pos)

    def assign_to(self, rider_id):
        """Mark order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, now):
        """Mark as completed."""
        self.status = "completed"
        self.complete_time = now

    @property
    def duration(self):
        """Ticks taken, or None."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.start_time

    def to_dict(self):
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "complete_time": self.complete_time,
                "distance": self.distance}
