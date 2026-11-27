"""Order data model."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import globalvar  # noqa: E402

CELL = 100


def to_grid(v):
    """Convert a coordinate to the top-left corner of its grid cell."""
    return (int(v) // CELL) * CELL


class Order:
    """A delivery order: restaurant position -> customer position."""

    def __init__(self, res_pos, cus_pos):
        n = (globalvar.get_value("order_id_counter") or 0) + 1
        globalvar.set_value("order_id_counter", n)
        self.id = n
        self.res_pos = (to_grid(res_pos[0]), to_grid(res_pos[1]))
        self.cus_pos = (to_grid(cus_pos[0]), to_grid(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick") or 0
        self.completion_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    @property
    def time_taken(self):
        """Ticks from creation to completion (None if not done)."""
        if self.completion_time is None:
            return None
        return self.completion_time - self.start_time

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"

    def to_dict(self):
        return {"id": self.id, "restaurant": list(self.res_pos),
                "customer": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "completion_time": self.completion_time,
                "distance": self.distance, "time_taken": self.time_taken}
