"""Order data model."""
import globalvar
from pathplanner import center


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        cnt = globalvar.get_value("order_counter", 0) + 1
        globalvar.set_value("order_counter", cnt)
        self.id = cnt
        self.res_pos = (center(res_pos[0]), center(res_pos[1]))
        self.cus_pos = (center(cus_pos[0]), center(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0)
        self.end_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))
        orders = globalvar.get_value("orders")
        if orders is not None:
            orders.append(self)

    def assign_to(self, rider_id):
        """Mark assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"
