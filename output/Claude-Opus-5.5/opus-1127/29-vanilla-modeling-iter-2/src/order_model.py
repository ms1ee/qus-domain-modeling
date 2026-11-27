"""Order data model."""

import globalvar
from grid_map import cell_index, to_grid_center
from path_planner import PathPlanner


class Order:
    """A delivery order from a restaurant to a customer.

    Input coordinates are converted to grid cell centres.
    """

    def __init__(self, res_pos, cus_pos, order_id=None, register=True):
        rx, ry = int(res_pos[0]), int(res_pos[1])
        cx, cy = int(cus_pos[0]), int(cus_pos[1])
        self.raw = [rx, ry, cx, cy]
        self.res_x = to_grid_center(rx)
        self.res_y = to_grid_center(ry)
        self.cus_x = to_grid_center(cx)
        self.cus_y = to_grid_center(cy)
        if order_id is None:
            order_id = globalvar.get_value("order_id_counter", 0) + 1
            globalvar.set_value("order_id_counter", order_id)
        self.id = order_id
        self.start_time = globalvar.get_value("current_tick", 0)
        self.status = "pending"
        self.rider_id = None
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.time_taken = None
        self.assign_distance = None
        planner = PathPlanner()
        self.distance = planner.path_length(planner.plan(self.res_pos, self.cus_pos))
        if register:
            orders = globalvar.get_value("orders")
            if orders is None:
                orders = []
                globalvar.set_value("orders", orders)
            orders.append(self)

    @property
    def res_pos(self):
        """Restaurant position (grid centre)."""
        return self.res_x, self.res_y

    @property
    def cus_pos(self):
        """Customer position (grid centre)."""
        return self.cus_x, self.cus_y

    @property
    def res_cell(self):
        """Restaurant grid cell indices."""
        return cell_index(self.res_x), cell_index(self.res_y)

    @property
    def cus_cell(self):
        """Customer grid cell indices."""
        return cell_index(self.cus_x), cell_index(self.cus_y)

    def as_list(self):
        """Return ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.res_x, self.res_y, self.cus_x, self.cus_y]

    def assign_to(self, rider_id):
        """Assign this order to the rider with ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assign_time = globalvar.get_value("current_tick", 0)

    def complete(self, tick=None):
        """Mark the order as completed at ``tick``."""
        if tick is None:
            tick = globalvar.get_value("current_tick", 0)
        self.status = "completed"
        self.complete_time = tick
        self.time_taken = tick - self.start_time

    def to_dict(self):
        """Serialise to a JSON-friendly dict."""
        return {
            "id": self.id, "raw": self.raw,
            "res": [self.res_x, self.res_y], "cus": [self.cus_x, self.cus_y],
            "start_time": self.start_time, "status": self.status,
            "rider_id": self.rider_id, "assign_time": self.assign_time,
            "accept_time": self.accept_time, "pickup_time": self.pickup_time,
            "complete_time": self.complete_time, "time_taken": self.time_taken,
            "assign_distance": self.assign_distance, "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order (not registered globally)."""
        order = cls(data["res"], data["cus"], order_id=data["id"], register=False)
        order.raw = list(data.get("raw", order.as_list()))
        for key in ("start_time", "status", "rider_id", "assign_time", "accept_time",
                    "pickup_time", "complete_time", "time_taken",
                    "assign_distance", "distance"):
            if key in data:
                setattr(order, key, data[key])
        return order

    def __repr__(self):
        return "Order(id=%s, res=%s, cus=%s, status=%s, rider=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status, self.rider_id)
