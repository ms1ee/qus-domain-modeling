"""Order data model."""

import globalvar
from grid_map import MAP_SIZE, to_cell_center, to_grid_index
from path_planner import PathPlanner


def _validate_pos(pos, label):
    try:
        x, y = pos
    except (TypeError, ValueError):
        raise ValueError("%s must be a pair of coordinates" % label)
    out = []
    for v in (x, y):
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("%s coordinates must be integers" % label)
        if v < 0 or v > MAP_SIZE:
            raise ValueError("%s coordinates must be in range 0-%d"
                             % (label, MAP_SIZE))
        out.append(v)
    return tuple(out)


class Order:
    """A delivery order from a restaurant to a customer.

    Raw coordinates are converted to grid cell centers.
    """

    _id_counter = 0

    def __init__(self, res_pos, cus_pos):
        res = _validate_pos(res_pos, "Restaurant")
        cus = _validate_pos(cus_pos, "Customer")
        Order._id_counter += 1
        self.id = Order._id_counter
        self.raw_res = res
        self.raw_cus = cus
        self.res_grid = (to_grid_index(res[0]), to_grid_index(res[1]))
        self.cus_grid = (to_grid_index(cus[0]), to_grid_index(cus[1]))
        self.res_pos = (to_cell_center(res[0]), to_cell_center(res[1]))
        self.cus_pos = (to_cell_center(cus[0]), to_cell_center(cus[1]))
        self.status = "pending"
        self.rider_id = None
        tick = globalvar.get_value("tick", 0)
        self.start_time = tick if tick is not None else 0
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.ticks_elapsed = 0
        self.travel_distance = 0
        self.distance = PathPlanner().distance(self.res_pos, self.cus_pos)
        self.paid = False

    # convenience accessors matching the data model
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
        """Record the assignment of this order to a rider."""
        self.rider_id = rider_id
        if self.status != "completed":
            self.status = "assigned"
        tick = globalvar.get_value("tick", 0)
        self.assign_time = tick if tick is not None else 0

    def to_dict(self):
        """Serialisable representation."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "raw_restaurant": list(self.raw_res),
            "raw_customer": list(self.raw_cus),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "travel_distance": self.travel_distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self):
        return "Order(#%d %s->%s %s)" % (self.id, self.res_pos, self.cus_pos,
                                        self.status)
