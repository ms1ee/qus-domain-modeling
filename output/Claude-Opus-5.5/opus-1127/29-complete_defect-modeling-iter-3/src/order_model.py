"""Order data model."""

import globalvar
from grid_map import to_cell_center, to_grid_index, validate_coordinate
from path_planner import PathPlanner


class OrderStatus:
    """Order lifecycle status values."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    PICKING_UP = "picking_up"
    DELIVERING = "delivering"
    COMPLETED = "completed"


def _current_time():
    t = globalvar.get_value("time")
    return t if isinstance(t, int) else 0


def _validate_pos(pos, name):
    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
        raise ValueError("%s must be a pair of coordinates" % name)
    return (validate_coordinate(pos[0], name + " x"),
            validate_coordinate(pos[1], name + " y"))


class Order:
    """A delivery order from a restaurant to a customer.

    Input coordinates are converted to grid cell centers.
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos, start_time=None, order_id=None):
        rx, ry = _validate_pos(res_pos, "restaurant")
        cx, cy = _validate_pos(cus_pos, "customer")
        if order_id is None:
            order_id = Order._next_id
        Order._next_id = max(Order._next_id, order_id + 1)
        self.id = order_id
        self.raw_res_pos = (rx, ry)
        self.raw_cus_pos = (cx, cy)
        self.res_pos = (to_cell_center(rx), to_cell_center(ry))
        self.cus_pos = (to_cell_center(cx), to_cell_center(cy))
        self.res_grid = (to_grid_index(rx), to_grid_index(ry))
        self.cus_grid = (to_grid_index(cx), to_grid_index(cy))
        self.start_time = _current_time() if start_time is None else start_time
        self.status = OrderStatus.PENDING
        self.rider_id = None
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.distance = PathPlanner().plan(self.res_pos,
                                           self.cus_pos).total_distance
        self.travel_distance = 0

    # Convenience attributes -------------------------------------------
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

    @classmethod
    def reset_counter(cls, start=1):
        """Reset the order id counter."""
        cls._next_id = start

    # Lifecycle ---------------------------------------------------------
    def assign_to(self, rider_id):
        """Record the assignment of this order to rider ``rider_id``."""
        self.rider_id = rider_id
        if self.status in (OrderStatus.PENDING, OrderStatus.ASSIGNED):
            self.status = OrderStatus.ASSIGNED
        self.assign_time = _current_time()

    def mark_picking_up(self, time):
        """Rider accepted the order and is heading to the restaurant."""
        self.status = OrderStatus.PICKING_UP
        self.accept_time = time

    def mark_picked_up(self, time):
        """Rider picked the food up at the restaurant."""
        self.status = OrderStatus.DELIVERING
        self.pickup_time = time

    def complete(self, time):
        """Mark the order completed at ``time``."""
        self.status = OrderStatus.COMPLETED
        self.completion_time = time
        self.time_taken = time - self.start_time

    @property
    def efficiency(self):
        """Distance (restaurant to customer) per tick of total time taken."""
        if not self.time_taken:
            return None
        return round(self.distance / self.time_taken, 2)

    # Persistence -------------------------------------------------------
    def to_dict(self):
        return {
            "id": self.id,
            "raw_res_pos": list(self.raw_res_pos),
            "raw_cus_pos": list(self.raw_cus_pos),
            "start_time": self.start_time,
            "status": self.status,
            "rider_id": self.rider_id,
            "assign_time": self.assign_time,
            "accept_time": self.accept_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "travel_distance": self.travel_distance,
        }

    @classmethod
    def from_dict(cls, data):
        order = cls(list(data["raw_res_pos"]), list(data["raw_cus_pos"]),
                    start_time=data.get("start_time", 0),
                    order_id=data["id"])
        for key in ("status", "rider_id", "assign_time", "accept_time",
                    "pickup_time", "completion_time", "time_taken",
                    "travel_distance"):
            if key in data:
                setattr(order, key, data[key])
        return order

    def __repr__(self):
        return "Order(#%d %s->%s %s)" % (self.id, self.res_pos, self.cus_pos,
                                         self.status)
