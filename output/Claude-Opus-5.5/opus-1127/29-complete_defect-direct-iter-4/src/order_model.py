"""Order data model."""

import globalvar
from path_planner import PathPlanner


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are converted to the centre of their grid cell.

    Attributes:
        id: unique order id.
        res_pos / cus_pos: grid-centre positions of restaurant / customer.
        raw_res / raw_cus: raw user input positions.
        status: "pending", "assigned", "picking_up", "delivering",
            "completed".
        rider_id: id of the assigned rider (or None).
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        self.id = Order._next_id
        Order._next_id += 1
        self.raw_res = (int(res_pos[0]), int(res_pos[1]))
        self.raw_cus = (int(cus_pos[0]), int(cus_pos[1]))
        self.res_pos = PathPlanner.to_center_pos(self.raw_res)
        self.cus_pos = PathPlanner.to_center_pos(self.raw_cus)
        self.res_grid = (PathPlanner.to_grid_index(self.raw_res[0]),
                         PathPlanner.to_grid_index(self.raw_res[1]))
        self.cus_grid = (PathPlanner.to_grid_index(self.raw_cus[0]),
                         PathPlanner.to_grid_index(self.raw_cus[1]))
        self.status = "pending"
        self.rider_id = None
        self.create_time = globalvar.get_value("time", 0)
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.time_taken = None
        self.travel_distance = None
        self.efficiency = None
        self.distance = PathPlanner.distance(self.res_pos, self.cus_pos)
        cfg = globalvar.get_value("config") or {}
        base = cfg.get("order_base_fee", 30)
        per = cfg.get("order_fee_per_100", 10)
        self.fee = int(base + per * self.distance // 100)

    @classmethod
    def reset_counter(cls, value=1):
        """Reset the order id counter."""
        cls._next_id = value

    def assign_to(self, rider_id):
        """Mark this order as assigned to ``rider_id``."""
        self.rider_id = rider_id
        if self.status in ("pending", "assigned"):
            self.status = "assigned"
        self.assign_time = globalvar.get_value("time", 0)

    def complete(self, travel_distance=None):
        """Mark the order as completed and record efficiency data."""
        self.status = "completed"
        self.complete_time = globalvar.get_value("time", 0)
        self.time_taken = self.complete_time - self.create_time
        self.travel_distance = travel_distance
        if self.time_taken and self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 2)
        else:
            self.efficiency = None

    def to_dict(self):
        """Serialise to a JSON compatible dict."""
        d = dict(self.__dict__)
        for k in ("raw_res", "raw_cus", "res_pos", "cus_pos",
                  "res_grid", "cus_grid"):
            d[k] = list(d[k])
        return d

    @classmethod
    def from_dict(cls, d):
        """Rebuild an order from :meth:`to_dict` output."""
        obj = cls.__new__(cls)
        for k, v in d.items():
            if k in ("raw_res", "raw_cus", "res_pos", "cus_pos",
                     "res_grid", "cus_grid"):
                v = tuple(v)
            setattr(obj, k, v)
        return obj

    def __repr__(self):
        return "Order(id=%s, res=%s, cus=%s, status=%s, rider=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status, self.rider_id)
