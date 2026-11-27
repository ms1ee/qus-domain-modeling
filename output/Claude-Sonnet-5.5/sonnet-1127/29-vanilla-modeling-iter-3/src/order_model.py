"""Order data model."""
import itertools

_counter = itertools.count(1)


class Order:
    """A delivery order. res_pos/cus_pos are (x, y) tuples."""

    def __init__(self, res_pos, cus_pos, start_time=None):
        import globalvar
        self.id = next(_counter)
        self.res_pos = tuple(res_pos)
        self.cus_pos = tuple(cus_pos)
        self.status = "pending"
        self.rider_id = None
        self.start_time = (globalvar.get_value("tick", 0)
                           if start_time is None else start_time)
        self.completion_time = None
        self.time_taken = None
        dx = self.res_pos[0] - self.cus_pos[0]
        dy = self.res_pos[1] - self.cus_pos[1]
        self.distance = (dx * dx + dy * dy) ** 0.5

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, time):
        """Mark as completed and record efficiency data."""
        self.status = "completed"
        self.completion_time = time
        self.time_taken = time - self.start_time

    def to_dict(self):
        return {"id": self.id, "restaurant": list(self.res_pos),
                "customer": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "completion_time": self.completion_time,
                "distance": self.distance, "time_taken": self.time_taken}
