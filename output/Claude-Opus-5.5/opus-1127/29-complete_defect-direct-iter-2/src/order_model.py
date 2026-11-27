"""Order data model."""

import globalvar
import config
from path_planner import PathPlanner


def _validate_pos(pos, name):
    """Validate a coordinate pair and return it as a tuple of ints."""
    try:
        x, y = pos
    except (TypeError, ValueError):
        raise ValueError("%s must contain two coordinates" % name)
    result = []
    for v in (x, y):
        if isinstance(v, bool):
            raise ValueError("%s coordinates must be integers" % name)
        try:
            iv = int(v)
        except (TypeError, ValueError):
            raise ValueError("%s coordinates must be integers" % name)
        if iv != v and not isinstance(v, str):
            raise ValueError("%s coordinates must be integers" % name)
        if iv < 0 or iv > config.MAP_SIZE:
            raise ValueError("%s coordinates must be within 0-%d"
                             % (name, config.MAP_SIZE))
        result.append(iv)
    return tuple(result)


class Order:
    """A delivery order from a restaurant to a customer.

    Statuses: ``pending`` -> ``assigned`` -> ``picking_up`` ->
    ``delivering`` -> ``completed``.
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        """Create an order; raw coordinates are converted to cell centres."""
        self.raw_res = _validate_pos(res_pos, "Restaurant")
        self.raw_cus = _validate_pos(cus_pos, "Customer")
        self.res_pos = (PathPlanner.to_grid_center(self.raw_res[0]),
                        PathPlanner.to_grid_center(self.raw_res[1]))
        self.cus_pos = (PathPlanner.to_grid_center(self.raw_cus[0]),
                        PathPlanner.to_grid_center(self.raw_cus[1]))
        self.id = Order._next_id
        Order._next_id += 1
        self.status = "pending"
        self.rider_id = None
        self.create_time = globalvar.get_value("tick", 0) or 0
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.fee = config.ORDER_FEE
        self.distance = PathPlanner().distance(self.res_pos, self.cus_pos)

    @classmethod
    def reset_counter(cls, value=1):
        """Reset the order id counter."""
        cls._next_id = value

    @property
    def res_grid(self):
        """Grid cell of the restaurant."""
        return PathPlanner.cell_of(*self.res_pos)

    @property
    def cus_grid(self):
        """Grid cell of the customer."""
        return PathPlanner.cell_of(*self.cus_pos)

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assign_time = globalvar.get_value("tick", 0) or 0

    def complete(self, time=None):
        """Mark the order as completed."""
        self.status = "completed"
        self.complete_time = (globalvar.get_value("tick", 0) or 0
                              if time is None else time)

    @property
    def time_taken(self):
        """Ticks from creation to completion (None if not completed)."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.create_time

    @property
    def efficiency(self):
        """Delivery efficiency in distance units per tick."""
        t = self.time_taken
        if not t:
            return None
        return round(self.distance / t, 2)

    def to_dict(self):
        """Serialise to a JSON compatible dict."""
        return {
            "id": self.id, "raw_res": list(self.raw_res),
            "raw_cus": list(self.raw_cus), "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos), "status": self.status,
            "rider_id": self.rider_id, "create_time": self.create_time,
            "assign_time": self.assign_time, "accept_time": self.accept_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time, "fee": self.fee,
            "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from :meth:`to_dict` output."""
        obj = cls.__new__(cls)
        obj.id = int(data["id"])
        obj.raw_res = tuple(data["raw_res"])
        obj.raw_cus = tuple(data["raw_cus"])
        obj.res_pos = tuple(data["res_pos"])
        obj.cus_pos = tuple(data["cus_pos"])
        obj.status = data.get("status", "pending")
        obj.rider_id = data.get("rider_id")
        obj.create_time = data.get("create_time", 0)
        obj.assign_time = data.get("assign_time")
        obj.accept_time = data.get("accept_time")
        obj.pickup_time = data.get("pickup_time")
        obj.complete_time = data.get("complete_time")
        obj.fee = data.get("fee", config.ORDER_FEE)
        obj.distance = data.get("distance", 0)
        if cls._next_id <= obj.id:
            cls._next_id = obj.id + 1
        return obj

    def __repr__(self):
        return "Order(id=%d, %s->%s, %s)" % (self.id, self.res_pos,
                                             self.cus_pos, self.status)
