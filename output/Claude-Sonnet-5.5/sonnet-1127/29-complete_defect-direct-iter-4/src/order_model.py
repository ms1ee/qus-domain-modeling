"""Order data model."""
import globalvar
from path_planner import to_center, PathPlanner


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        n = (globalvar.get_value("order_id_counter", 0) or 0) + 1
        globalvar.set_value("order_id_counter", n)
        self.id = n
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0) or 0
        self.complete_time = None
        self.distance = PathPlanner.distance(self.res_pos, self.cus_pos)

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self):
        """Mark as completed."""
        self.status = "completed"
        self.complete_time = globalvar.get_value("time", 0) or 0

    @property
    def time_taken(self):
        if self.complete_time is None:
            return None
        return self.complete_time - self.start_time

    def to_dict(self):
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "complete_time": self.complete_time,
                "distance": self.distance}
