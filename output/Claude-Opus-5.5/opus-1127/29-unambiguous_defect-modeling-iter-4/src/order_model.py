"""Order data model."""

import globalvar
from grid_map import GridMap
from path_planner import PathPlanner

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _to_int(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"{label} must be an integer")
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            raise ValueError(f"{label} must be an integer") from None
    raise ValueError(f"{label} must be an integer")


def _parse_point(pos, label):
    try:
        if len(pos) != 2:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError(f"{label} position must contain two coordinates") from None
    return _to_int(pos[0], f"{label} x"), _to_int(pos[1], f"{label} y")


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are automatically converted to grid cell centres.

    Attributes:
        id: Unique order id.
        status: "pending", "assigned", "picking_up", "delivering", "completed".
    """

    def __init__(self, res_pos, cus_pos):
        rx, ry = _parse_point(res_pos, "restaurant")
        cx, cy = _parse_point(cus_pos, "customer")
        self.raw_input = [rx, ry, cx, cy]
        self.restaurant_x, self.restaurant_y = GridMap.to_center_point(rx, ry)
        self.customer_x, self.customer_y = GridMap.to_center_point(cx, cy)

        counter = int(globalvar.get_value("order_id_counter", 0) or 0) + 1
        globalvar.set_value("order_id_counter", counter)
        self.id = counter
        self.status = STATUS_PENDING
        self.rider_id = None
        self.start_time = int(globalvar.get_value("current_time", 0) or 0)
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.efficiency = None
        self.distance = PathPlanner.distance(self.res_pos, self.cus_pos)

        orders = globalvar.get_value("orders")
        if not isinstance(orders, list):
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(self)

    @property
    def order_id(self):
        """Alias of :attr:`id`."""
        return self.id

    @property
    def res_pos(self):
        """Restaurant position (grid centre)."""
        return (self.restaurant_x, self.restaurant_y)

    @property
    def cus_pos(self):
        """Customer position (grid centre)."""
        return (self.customer_x, self.customer_y)

    def as_list(self):
        """Return ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.restaurant_x, self.restaurant_y, self.customer_x, self.customer_y]

    def assign_to(self, rider_id):
        """Assign the order to the rider with ``rider_id``."""
        self.rider_id = rider_id
        if self.status == STATUS_PENDING:
            self.status = STATUS_ASSIGNED
        self.assign_time = int(globalvar.get_value("current_time", 0) or 0)

    def is_completed(self):
        """True once the order has been delivered."""
        return self.status == STATUS_COMPLETED

    def complete(self, time):
        """Mark the order as delivered at ``time``."""
        self.status = STATUS_COMPLETED
        self.completion_time = int(time)
        self.time_taken = self.completion_time - self.start_time
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 2)
        else:
            self.efficiency = None

    def to_dict(self):
        """Serialise the order."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "raw_input": list(self.raw_input),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "assign_time": self.assign_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "efficiency": self.efficiency,
        }

    def __repr__(self):
        return (f"Order(id={self.id}, res={self.res_pos}, cus={self.cus_pos}, "
                f"status={self.status}, rider={self.rider_id})")
