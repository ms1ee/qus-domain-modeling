"""Order model."""
import globalvar


def to_center(v):
    """Convert coordinate to grid cell center (clamped to the map)."""
    v = max(0, min(int(v), 799))
    return (v // 100) * 100 + 50


class Order:
    """A delivery order."""

    _counter = 0

    def __init__(self, res_pos, cus_pos):
        Order._counter += 1
        self.id = Order._counter
        self.res_pos = [to_center(res_pos[0]), to_center(res_pos[1])]
        self.cus_pos = [to_center(cus_pos[0]), to_center(cus_pos[1])]
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0) or 0
        self.completion_time = None
        self.time_taken = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0]) +
                         abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"
        self.start_time = globalvar.get_value("tick", 0) or 0

    def complete(self, tick):
        """Mark delivered and record efficiency data."""
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = tick - self.start_time

    def to_dict(self):
        return {"id": self.id, "res_pos": self.res_pos,
                "cus_pos": self.cus_pos, "status": self.status,
                "rider_id": self.rider_id, "start_time": self.start_time,
                "completion_time": self.completion_time,
                "distance": self.distance, "time_taken": self.time_taken}
