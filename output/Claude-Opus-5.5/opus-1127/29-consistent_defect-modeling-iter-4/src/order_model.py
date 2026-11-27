"""Order data model."""

import globalvar
from path_planner import GridMap, manhattan

_grid = GridMap()


def _next_order_id():
    counter = globalvar.get_value("order_id_counter", 0) or 0
    counter += 1
    globalvar.set_value("order_id_counter", counter)
    return counter


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are converted to the top-left corner of their grid cell.
    Status values: "pending", "assigned", "picked_up", "completed".
    """

    def __init__(self, res_pos, cus_pos):
        self.id = _next_order_id()
        self.raw_res_pos = (int(res_pos[0]), int(res_pos[1]))
        self.raw_cus_pos = (int(cus_pos[0]), int(cus_pos[1]))
        self.res_pos = _grid.to_grid_corner(*self.raw_res_pos)
        self.cus_pos = _grid.to_grid_corner(*self.raw_cus_pos)
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("current_tick", 0) or 0
        self.accept_time = None
        self.completion_time = None
        self.distance = manhattan(self.res_pos, self.cus_pos)
        self.time_taken = None
        self.efficiency = None
        orders = globalvar.get_value("orders")
        if isinstance(orders, list):
            orders.append(self)

    @property
    def completed(self):
        """True once the order was delivered."""
        return self.status == "completed"

    def assign_to(self, rider_id):
        """Assign the order to the rider with ``rider_id``.

        The order is appended to that rider's order list (if the rider is
        registered and does not already hold this order).
        """
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        for rider in globalvar.get_value("riders") or []:
            if getattr(rider, "rider_id", None) == rider_id:
                if not any(o is self for o in rider.orders):
                    rider.orders.append(self)
                break

    def complete(self, time):
        """Mark the order completed at ``time``."""
        self.status = "completed"
        self.completion_time = time
        self.time_taken = time - self.start_time
        if self.time_taken and self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 2)

    def to_dict(self):
        """Serialise to a dict."""
        return {
            "id": self.id,
            "raw_res_pos": list(self.raw_res_pos),
            "raw_cus_pos": list(self.raw_cus_pos),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "accept_time": self.accept_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild from :meth:`to_dict` output (not re-registered)."""
        order = cls.__new__(cls)
        order.id = data["id"]
        order.raw_res_pos = tuple(data.get("raw_res_pos", data["res_pos"]))
        order.raw_cus_pos = tuple(data.get("raw_cus_pos", data["cus_pos"]))
        order.res_pos = tuple(data["res_pos"])
        order.cus_pos = tuple(data["cus_pos"])
        order.status = data["status"]
        order.rider_id = data.get("rider_id")
        order.start_time = data.get("start_time", 0)
        order.accept_time = data.get("accept_time")
        order.completion_time = data.get("completion_time")
        order.distance = data.get("distance", 0)
        order.time_taken = data.get("time_taken")
        order.efficiency = data.get("efficiency")
        return order

    def __repr__(self):
        return "Order(id=%s, res=%s, cus=%s, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
