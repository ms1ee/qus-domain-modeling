"""Order data model."""

import globalvar
from path_planner import PathPlanner, manhattan, to_grid_point


def _validate_pos(pos, name):
    """Validate a coordinate pair and return it as an integer tuple."""
    try:
        if len(pos) != 2:
            raise ValueError
        return (int(pos[0]), int(pos[1]))
    except (TypeError, ValueError):
        raise ValueError("%s must be a pair of integers" % name)


def _next_order_id():
    """Return the next unique order id."""
    counter = globalvar.get_value("order_id_counter", 0) or 0
    counter += 1
    globalvar.set_value("order_id_counter", counter)
    return counter


class Order:
    """A delivery order from a restaurant to a customer.

    Attributes:
        id: unique order id.
        raw_res / raw_cus: coordinates as entered.
        res_pos / cus_pos: grid cell centers of restaurant / customer.
        status: "pending", "assigned", "picking_up", "delivering",
            "completed".
        rider_id: id of the assigned rider (None until assigned).
    """

    def __init__(self, res_pos, cus_pos):
        self.raw_res = _validate_pos(res_pos, "res_pos")
        self.raw_cus = _validate_pos(cus_pos, "cus_pos")
        self.res_pos = to_grid_point(self.raw_res)
        self.cus_pos = to_grid_point(self.raw_cus)
        self.id = _next_order_id()
        self.status = "pending"
        self.rider_id = None
        self.created_time = globalvar.get_value("time", 0) or 0
        self.assigned_time = None
        self.accepted_time = None
        self.picked_time = None
        self.completed_time = None
        self.time_taken = None
        self.distance = manhattan(self.res_pos, self.cus_pos)
        planner = PathPlanner()
        self.route_distance = planner.path_length(
            self.res_pos, planner.plan(self.res_pos, self.cus_pos))

    def assign_to(self, rider_id):
        """Record that this order is assigned to ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assigned_time = globalvar.get_value("time", 0) or 0

    def to_dict(self):
        """Serializable representation of the order."""
        return {
            "id": self.id,
            "raw_res": list(self.raw_res),
            "raw_cus": list(self.raw_cus),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_time": self.created_time,
            "assigned_time": self.assigned_time,
            "picked_time": self.picked_time,
            "completed_time": self.completed_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "route_distance": self.route_distance,
        }

    def __repr__(self):
        return "Order(id=%s, res=%s, cus=%s, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
