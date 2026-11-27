"""Order data model."""

import globalvar
from path_planner import PathPlanner


class OrderStatus:
    """Possible order statuses."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    PICKING_UP = "picking_up"
    DELIVERING = "delivering"
    COMPLETED = "completed"


def _validate_pos(pos, name):
    try:
        if len(pos) != 2:
            raise ValueError
        return int(pos[0]), int(pos[1])
    except (TypeError, ValueError):
        raise ValueError("%s must be a pair of integers" % name)


class Order:
    """A delivery order from a restaurant to a customer.

    Input coordinates are converted to grid cell centres.

    Attributes:
        id: unique order id.
        raw_res_pos / raw_cus_pos: coordinates as entered.
        res_pos / cus_pos: grid centre coordinates.
        restaurant_x, restaurant_y, customer_x, customer_y: same values.
        status: "pending", "assigned", "picking_up", "delivering", "completed".
        rider_id: id of the assigned rider (or None).
        start_time, assign_time, pickup_time, completion_time: ticks.
        distance: street distance restaurant -> customer.
        time_taken: completion_time - start_time once completed.
    """

    def __init__(self, res_pos, cus_pos, start_time=None):
        res = _validate_pos(res_pos, "res_pos")
        cus = _validate_pos(cus_pos, "cus_pos")
        self.raw_res_pos = res
        self.raw_cus_pos = cus
        self.res_pos = PathPlanner.to_grid_center(*res)
        self.cus_pos = PathPlanner.to_grid_center(*cus)
        self.restaurant_x, self.restaurant_y = self.res_pos
        self.customer_x, self.customer_y = self.cus_pos
        counter = globalvar.get_value("order_id_counter", 0) or 0
        counter += 1
        globalvar.set_value("order_id_counter", counter)
        self.id = counter
        self.status = OrderStatus.PENDING
        self.rider_id = None
        if start_time is None:
            start_time = globalvar.get_value("tick", 0) or 0
        self.start_time = start_time
        self.assign_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.distance = PathPlanner.street_distance(
            PathPlanner.access_point(self.res_pos),
            PathPlanner.access_point(self.cus_pos))
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(self)

    @property
    def completed(self):
        """True once the order has been delivered."""
        return self.status == OrderStatus.COMPLETED

    @property
    def res_access(self):
        """Street point where the rider picks up the order."""
        return PathPlanner.access_point(self.res_pos)

    @property
    def cus_access(self):
        """Street point where the rider hands over the order."""
        return PathPlanner.access_point(self.cus_pos)

    def assign_to(self, rider_id):
        """Assign the order to the rider with id ``rider_id``."""
        self.rider_id = rider_id
        if self.status == OrderStatus.PENDING:
            self.status = OrderStatus.ASSIGNED
        self.assign_time = globalvar.get_value("tick", 0) or 0

    def mark_picking_up(self):
        """Rider is heading to the restaurant."""
        if self.status != OrderStatus.COMPLETED:
            self.status = OrderStatus.PICKING_UP

    def mark_picked_up(self, time):
        """Rider picked the food up at the restaurant."""
        self.pickup_time = time
        self.status = OrderStatus.DELIVERING

    def complete(self, time):
        """Mark the order delivered at ``time``."""
        self.completion_time = time
        self.time_taken = time - (self.start_time or 0)
        self.status = OrderStatus.COMPLETED

    def to_dict(self):
        """Serialise to a JSON friendly dict."""
        return {
            "id": self.id,
            "raw_res_pos": list(self.raw_res_pos),
            "raw_cus_pos": list(self.raw_cus_pos),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "assign_time": self.assign_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from :meth:`to_dict` output (not registered)."""
        obj = cls.__new__(cls)
        obj.id = int(data["id"])
        obj.raw_res_pos = tuple(data.get("raw_res_pos", data["res_pos"]))
        obj.raw_cus_pos = tuple(data.get("raw_cus_pos", data["cus_pos"]))
        obj.res_pos = tuple(data["res_pos"])
        obj.cus_pos = tuple(data["cus_pos"])
        obj.restaurant_x, obj.restaurant_y = obj.res_pos
        obj.customer_x, obj.customer_y = obj.cus_pos
        obj.status = data.get("status", OrderStatus.PENDING)
        obj.rider_id = data.get("rider_id")
        obj.start_time = data.get("start_time", 0)
        obj.assign_time = data.get("assign_time")
        obj.pickup_time = data.get("pickup_time")
        obj.completion_time = data.get("completion_time")
        obj.time_taken = data.get("time_taken")
        obj.distance = data.get("distance", 0)
        return obj

    def __repr__(self):
        return "Order(id=%d, res=%r, cus=%r, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
