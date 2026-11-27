"""Order data model."""

import globalvar
from path_planner import PathPlanner


def _now():
    t = globalvar.get_value("time", 0)
    return t if isinstance(t, int) else 0


class Order:
    """A delivery order.

    Input coordinates (0..800) are converted to grid cell centres.

    Attributes:
        id: auto incrementing order id.
        res_pos / cus_pos: restaurant / customer grid centre coordinates.
        status: "pending", "assigned", "picking_up", "delivering", "completed".
        rider_id: id of the assigned rider (or None).
        create_time, assign_time, accept_time, pickup_time, complete_time.
        distance: street distance from restaurant to customer.
    """

    def __init__(self, res_pos, cus_pos):
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("positions must be (x, y) pairs")
        oid = (globalvar.get_value("order_id_counter", 0) or 0) + 1
        globalvar.set_value("order_id_counter", oid)
        self.id = oid
        self.raw_res = (int(res_pos[0]), int(res_pos[1]))
        self.raw_cus = (int(cus_pos[0]), int(cus_pos[1]))
        self.res_pos = PathPlanner.to_grid_center(*self.raw_res)
        self.cus_pos = PathPlanner.to_grid_center(*self.raw_cus)
        self.status = "pending"
        self.rider_id = None
        self.create_time = _now()
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.distance = PathPlanner.path_length(
            self.res_pos, PathPlanner.plan(self.res_pos, self.cus_pos))
        orders = globalvar.get_value("orders")
        if isinstance(orders, list):
            orders.append(self)

    def assign_to(self, rider_id):
        """Mark the order as assigned to ``rider_id``."""
        self.rider_id = rider_id
        self.assign_time = _now()
        if self.status == "pending":
            self.status = "assigned"

    @property
    def time_taken(self):
        """Ticks from creation to completion (None if not completed)."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.create_time

    @property
    def efficiency(self):
        """Delivery distance per tick (None if unavailable)."""
        t = self.time_taken
        if not t:
            return None
        return round(self.distance / t, 2)

    def to_list(self):
        """Return [restaurant_x, restaurant_y, customer_x, customer_y]."""
        return [self.res_pos[0], self.res_pos[1], self.cus_pos[0], self.cus_pos[1]]

    def to_dict(self):
        """Serializable representation."""
        return {
            "id": self.id,
            "input": [self.raw_res[0], self.raw_res[1], self.raw_cus[0], self.raw_cus[1]],
            "coords": self.to_list(),
            "status": self.status,
            "rider_id": self.rider_id,
            "create_time": self.create_time,
            "assign_time": self.assign_time,
            "accept_time": self.accept_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }

    def __repr__(self):
        return "Order(id=%d, %s -> %s, %s)" % (self.id, self.res_pos, self.cus_pos, self.status)
