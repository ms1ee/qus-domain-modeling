"""Order model."""

import math
import globalvar


def to_cell(v):
    """Convert coordinate to top-left corner of its grid cell."""
    v = max(0, min(int(v), 800))
    return min(v // 100 * 100, 700)


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        n = globalvar.get_value("order_id_counter", 0) + 1
        globalvar.set_value("order_id_counter", n)
        self.id = n
        self.res_pos = (to_cell(res_pos[0]), to_cell(res_pos[1]))
        self.cus_pos = (to_cell(cus_pos[0]), to_cell(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0)
        self.completion_time = None
        self.time_taken = None
        self.distance = math.hypot(self.res_pos[0] - self.cus_pos[0],
                                   self.res_pos[1] - self.cus_pos[1])

    def assign_to(self, rider_id):
        """Mark as assigned to a rider."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"

    def to_dict(self):
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "completion_time": self.completion_time,
                "distance": self.distance, "time_taken": self.time_taken}
