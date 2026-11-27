"""Order model."""
import globalvar
from path_planner import to_center


class Order:
    """A delivery order."""
    _counter = 0

    def __init__(self, res_pos, cus_pos):
        Order._counter += 1
        self.id = Order._counter
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.create_time = globalvar.get_value("tick", 0)
        self.complete_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Mark order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def to_dict(self):
        """Serializable form."""
        return {"id": self.id, "res": list(self.res_pos),
                "cus": list(self.cus_pos), "status": self.status,
                "rider_id": self.rider_id, "start": self.create_time,
                "end": self.complete_time, "distance": self.distance}
