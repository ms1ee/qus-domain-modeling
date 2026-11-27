"""Order data model."""
import itertools

import globalvar

_ids = itertools.count(1)


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_ids)
        self.res_pos = tuple(res_pos)
        self.cus_pos = tuple(cus_pos)
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0) or 0
        self.end_time = None

    def assign_to(self, rider_id):
        """Mark order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    @property
    def distance(self):
        """Manhattan distance restaurant -> customer."""
        return (abs(self.res_pos[0] - self.cus_pos[0])
                + abs(self.res_pos[1] - self.cus_pos[1]))

    def to_dict(self):
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "end_time": self.end_time}
