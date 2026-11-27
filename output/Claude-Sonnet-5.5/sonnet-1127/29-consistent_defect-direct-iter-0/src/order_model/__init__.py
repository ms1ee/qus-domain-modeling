"""Order data model."""
import globalvar


def to_cell(v):
    """Convert a coordinate to its grid cell top-left corner (0-700)."""
    return max(0, min(700, (int(v) // 100) * 100))


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        n = (globalvar.get_value("order_counter") or 0) + 1
        globalvar.set_value("order_counter", n)
        self.id = n
        self.res_pos = [to_cell(res_pos[0]), to_cell(res_pos[1])]
        self.cus_pos = [to_cell(cus_pos[0]), to_cell(cus_pos[1])]
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time") or 0
        self.end_time = None
        self.picked = False
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))
        orders = globalvar.get_value("orders")
        if orders is not None:
            orders.append(self)

    def assign_to(self, rider_id):
        """Assign order to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    def to_dict(self):
        return {"id": self.id, "res": self.res_pos, "cus": self.cus_pos,
                "status": self.status, "rider": self.rider_id,
                "start": self.start_time, "end": self.end_time,
                "distance": self.distance}
