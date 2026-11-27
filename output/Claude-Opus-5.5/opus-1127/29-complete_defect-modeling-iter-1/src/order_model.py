"""Order data model."""

import globalvar
from grid_map import to_cell_center_point, to_grid_point
from path_planner import PathPlanner


class Order:
    """A delivery order from a restaurant to a customer.

    Input coordinates are converted to grid cell centers.
    Status lifecycle: pending -> assigned -> picking_up -> delivering -> completed
    """

    def __init__(self, res_pos, cus_pos, start_time=None):
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("positions must be (x, y) pairs")
        counter = globalvar.get_value("order_id_counter", 0) + 1
        globalvar.set_value("order_id_counter", counter)
        self.id = counter
        self.raw_res = (int(res_pos[0]), int(res_pos[1]))
        self.raw_cus = (int(cus_pos[0]), int(cus_pos[1]))
        self.res_pos = to_cell_center_point(self.raw_res)
        self.cus_pos = to_cell_center_point(self.raw_cus)
        self.res_grid = to_grid_point(self.raw_res)
        self.cus_grid = to_grid_point(self.raw_cus)
        self.start_time = globalvar.get_value("time", 0) if start_time is None else start_time
        self.status = "pending"
        self.rider_id = None
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.distance = PathPlanner().distance(self.res_pos, self.cus_pos)
        base = globalvar.get_value("base_fee", 30)
        per = globalvar.get_value("fee_per_100_units", 10)
        self.fee = int(base + (self.distance // 100) * per)

    @property
    def restaurant_x(self):
        return self.res_pos[0]

    @property
    def restaurant_y(self):
        return self.res_pos[1]

    @property
    def customer_x(self):
        return self.cus_pos[0]

    @property
    def customer_y(self):
        return self.cus_pos[1]

    def assign_to(self, rider_id):
        """Mark the order as assigned to ``rider_id``."""
        self.rider_id = rider_id
        self.status = "assigned"
        self.assign_time = globalvar.get_value("time", 0)

    def to_dict(self):
        """Serializable representation."""
        return {
            "id": self.id,
            "raw_restaurant": list(self.raw_res),
            "raw_customer": list(self.raw_cus),
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "rider_id": self.rider_id,
            "status": self.status,
            "fee": self.fee,
        }

    def __repr__(self):
        return "Order(#%d %s->%s %s)" % (self.id, self.res_pos, self.cus_pos, self.status)
