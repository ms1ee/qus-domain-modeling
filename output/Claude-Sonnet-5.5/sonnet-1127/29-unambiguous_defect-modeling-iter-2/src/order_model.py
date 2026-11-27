"""Order data model."""
import itertools

from pathplanner import to_center, PathPlanner
import globalvar

_counter = itertools.count(1)


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.id = next(_counter)
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick") or 0
        self.completion_time = None
        self.distance = PathPlanner.distance(self.res_pos, self.cus_pos)
        self.time_taken = None

    def assign_to(self, rider_id):
        """Assign this order to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, tick):
        """Mark as completed."""
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = tick - self.start_time
