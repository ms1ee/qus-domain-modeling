"""Order data model."""

import itertools

try:
    from src import globalvar
    from src.path_planner import to_center
except ImportError:  # pragma: no cover
    import globalvar
    from path_planner import to_center

_counter = itertools.count(1)


class Order:
    """A delivery order; positions are converted to grid cell centers."""

    def __init__(self, res_pos, cus_pos):
        self.id = next(_counter)
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0) or 0
        self.completion_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0]) +
                         abs(self.res_pos[1] - self.cus_pos[1]))
        self.time_taken = None
        self.efficiency = None

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def to_dict(self):
        """Serialize to dict."""
        return {"id": self.id, "res_pos": list(self.res_pos),
                "cus_pos": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "completion_time": self.completion_time,
                "distance": self.distance, "time_taken": self.time_taken,
                "efficiency": self.efficiency}
