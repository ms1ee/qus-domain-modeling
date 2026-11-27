"""Order data model."""

import globalvar
from path_planner import PathPlanner

BASE_FEE = 50


def _validate_pos(pos, name):
    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
        raise ValueError("%s must be a pair of coordinates" % name)
    for v in pos:
        PathPlanner.validate_coordinate(v)
    return (int(pos[0]), int(pos[1]))


class Order:
    """A delivery order from a restaurant to a customer.

    Raw coordinates are converted to grid cell centres.
    Status lifecycle: pending -> assigned -> picking_up -> delivering
    -> completed.
    """

    def __init__(self, res_pos, cus_pos):
        raw_res = _validate_pos(res_pos, "restaurant position")
        raw_cus = _validate_pos(cus_pos, "customer position")
        self.raw_res = raw_res
        self.raw_cus = raw_cus
        self.res_pos = PathPlanner.to_grid_center(*raw_res)
        self.cus_pos = PathPlanner.to_grid_center(*raw_cus)
        self.res_grid = (PathPlanner.to_grid_index(raw_res[0]),
                         PathPlanner.to_grid_index(raw_res[1]))
        self.cus_grid = (PathPlanner.to_grid_index(raw_cus[0]),
                         PathPlanner.to_grid_index(raw_cus[1]))
        new_id = globalvar.get_value("order_id_counter", 0) + 1
        globalvar.set_value("order_id_counter", new_id)
        self.id = new_id
        self.status = "pending"
        self.rider_id = None
        self.create_time = globalvar.get_value("time", 0)
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.time_taken = None
        self.distance = PathPlanner.path_length(self.res_pos, self.cus_pos)
        self.fee = BASE_FEE + self.distance // 10

    def assign_to(self, rider_id):
        """Mark this order as assigned to ``rider_id``."""
        self.rider_id = rider_id
        self.status = "assigned"
        self.assign_time = globalvar.get_value("time", 0)

    def mark_accepted(self, rider_id=None):
        if rider_id is not None:
            self.rider_id = rider_id
        self.status = "picking_up"
        self.accept_time = globalvar.get_value("time", 0)

    def mark_picked_up(self):
        self.status = "delivering"
        self.pickup_time = globalvar.get_value("time", 0)

    def mark_completed(self, now=None):
        if now is None:
            now = globalvar.get_value("time", 0)
        self.status = "completed"
        self.complete_time = now
        self.time_taken = now - self.create_time

    @property
    def efficiency(self):
        """Distance per tick of total order time (None until completed)."""
        if not self.time_taken:
            return None
        return round(self.distance / self.time_taken, 2)

    def to_list(self):
        return [self.res_pos[0], self.res_pos[1],
                self.cus_pos[0], self.cus_pos[1]]

    def to_dict(self):
        return {
            "id": self.id,
            "raw": [self.raw_res[0], self.raw_res[1],
                    self.raw_cus[0], self.raw_cus[1]],
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "create_time": self.create_time,
            "accept_time": self.accept_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "fee": self.fee,
        }

    def __repr__(self):
        return "Order(id=%s, res=%s, cus=%s, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
