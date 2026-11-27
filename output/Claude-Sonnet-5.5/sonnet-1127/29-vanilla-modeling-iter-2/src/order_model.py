"""Order data model."""
import globalvar


def to_center(v):
    """Convert a coordinate to its grid cell center."""
    v = max(0, min(799, int(v)))
    return (v // 100) * 100 + 50


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        cnt = globalvar.get_value("order_id_counter", 0) + 1
        globalvar.set_value("order_id_counter", cnt)
        self.id = cnt
        self.res_pos = (to_center(res_pos[0]), to_center(res_pos[1]))
        self.cus_pos = (to_center(cus_pos[0]), to_center(cus_pos[1]))
        self.status = "created"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0)
        self.completion_time = None
        d = ((self.res_pos[0] - self.cus_pos[0]) ** 2 +
             (self.res_pos[1] - self.cus_pos[1]) ** 2) ** 0.5
        self.distance = d
        orders = globalvar.get_value("orders")
        if orders is not None:
            orders.append(self)

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"

    @property
    def time_taken(self):
        if self.completion_time is None:
            return None
        return self.completion_time - self.start_time
