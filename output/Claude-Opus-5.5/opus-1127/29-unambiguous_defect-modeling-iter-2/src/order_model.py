"""Order data model."""

import globalvar
from path_planner import DEFAULT_GRID, manhattan


def _next_order_id():
    counter = (globalvar.get_value("order_id_counter", 0) or 0) + 1
    globalvar.set_value("order_id_counter", counter)
    return counter


def _pair(pos, name):
    try:
        x, y = pos
        return int(x), int(y)
    except (TypeError, ValueError):
        raise ValueError("%s must be a pair of integers" % name)


class Order:
    """A delivery order from a restaurant to a customer.

    Input coordinates are automatically converted to grid cell centres.
    Status lifecycle: pending -> assigned -> picking_up -> delivering ->
    completed.
    """

    def __init__(self, res_pos, cus_pos, start_time=None):
        rx, ry = _pair(res_pos, "res_pos")
        cx, cy = _pair(cus_pos, "cus_pos")
        self.id = _next_order_id()
        self.raw_res_pos = (rx, ry)
        self.raw_cus_pos = (cx, cy)
        self.res_pos = (DEFAULT_GRID.to_grid_center(rx),
                        DEFAULT_GRID.to_grid_center(ry))
        self.cus_pos = (DEFAULT_GRID.to_grid_center(cx),
                        DEFAULT_GRID.to_grid_center(cy))
        self.status = "pending"
        self.rider_id = None
        if start_time is None:
            start_time = globalvar.get_value("tick", 0) or 0
        self.start_time = int(start_time)
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.pickup_point = None
        self.dropoff_point = None
        self.distance = manhattan(self.res_pos, self.cus_pos)
        self.efficiency = None

    # Convenience accessors matching the [rx, ry, cx, cy] format.
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

    @property
    def completed(self):
        """True once the order has been delivered."""
        return self.status == "completed"

    def as_list(self):
        """Return ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.res_pos[0], self.res_pos[1],
                self.cus_pos[0], self.cus_pos[1]]

    def assign_to(self, rider_id):
        """Assign this order to the rider with ``rider_id``."""
        self.rider_id = rider_id
        self.assign_time = globalvar.get_value("tick", 0) or 0
        if self.status == "pending":
            self.status = "assigned"

    def to_dict(self):
        """JSON-serialisable representation."""
        return {
            "id": self.id,
            "raw_restaurant": list(self.raw_res_pos),
            "raw_customer": list(self.raw_cus_pos),
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "efficiency": self.efficiency,
        }

    def __repr__(self):
        return "Order(#%d %s->%s %s)" % (self.id, self.res_pos,
                                         self.cus_pos, self.status)
