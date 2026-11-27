"""Order data model."""

import globalvar
from grid_map import (CELL_SIZE, MAP_SIZE, clamp_coordinate, to_cell_center,
                      to_grid_index)
from path_planner import PathPlanner

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _to_int(value):
    if isinstance(value, bool):
        raise ValueError("coordinates must be integers")
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("coordinates must be integers")
        return int(value)
    return int(value)


def _next_order_id():
    counter = globalvar.get_value("order_id_counter", 0) or 0
    counter += 1
    globalvar.set_value("order_id_counter", counter)
    return counter


class Order:
    """A delivery order from a restaurant to a customer.

    Input coordinates (0-800) are converted to grid cell centers.
    """

    def __init__(self, res_pos, cus_pos, start_time=None, order_id=None):
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("positions must be (x, y) pairs")
        rx, ry = (clamp_coordinate(_to_int(v), MAP_SIZE) for v in res_pos)
        cx, cy = (clamp_coordinate(_to_int(v), MAP_SIZE) for v in cus_pos)
        self.raw_restaurant = (rx, ry)
        self.raw_customer = (cx, cy)
        self.restaurant = (to_cell_center(rx), to_cell_center(ry))
        self.customer = (to_cell_center(cx), to_cell_center(cy))
        self.restaurant_grid = (to_grid_index(rx), to_grid_index(ry))
        self.customer_grid = (to_grid_index(cx), to_grid_index(cy))
        if order_id is None:
            self.id = _next_order_id()
        else:
            self.id = int(order_id)
            if self.id > (globalvar.get_value("order_id_counter", 0) or 0):
                globalvar.set_value("order_id_counter", self.id)
        if start_time is None:
            start_time = globalvar.get_value("tick", 0) or 0
        self.start_time = int(start_time)
        self.status = STATUS_PENDING
        self.rider_id = None
        self.accept_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.active_ticks = 0
        self.fee = 0
        self.efficiency = None
        self.distance = PathPlanner(CELL_SIZE, MAP_SIZE).distance(
            self.restaurant, self.customer)

    # convenience accessors -------------------------------------------------
    @property
    def order_id(self):
        """Alias of ``id``."""
        return self.id

    @property
    def restaurant_x(self):
        return self.restaurant[0]

    @property
    def restaurant_y(self):
        return self.restaurant[1]

    @property
    def customer_x(self):
        return self.customer[0]

    @property
    def customer_y(self):
        return self.customer[1]

    def as_list(self):
        """Return [restaurant_x, restaurant_y, customer_x, customer_y]."""
        return [self.restaurant[0], self.restaurant[1],
                self.customer[0], self.customer[1]]

    # lifecycle -------------------------------------------------------------
    def assign_to(self, rider_id):
        """Assign the order to a rider (by id)."""
        self.rider_id = rider_id
        if self.status == STATUS_PENDING:
            self.status = STATUS_ASSIGNED

    def mark_accepted(self, tick, rider_id=None):
        """Rider accepted the order and heads to the restaurant."""
        if rider_id is not None and self.rider_id is None:
            self.rider_id = rider_id
        self.accept_time = tick
        self.status = STATUS_PICKING_UP

    def mark_picked_up(self, tick):
        """Rider picked up the food."""
        self.pickup_time = tick
        self.status = STATUS_DELIVERING

    def complete(self, tick):
        """Order delivered: record completion time and efficiency."""
        self.completion_time = tick
        elapsed = tick - self.start_time
        self.time_taken = elapsed if elapsed > 0 else self.active_ticks
        self.status = STATUS_COMPLETED
        if self.time_taken:
            self.efficiency = round(self.distance / self.time_taken, 2)
        else:
            self.efficiency = float(self.distance)

    def is_completed(self):
        return self.status == STATUS_COMPLETED

    # persistence -----------------------------------------------------------
    def to_dict(self):
        return {
            "id": self.id, "raw_restaurant": list(self.raw_restaurant),
            "raw_customer": list(self.raw_customer),
            "restaurant": list(self.restaurant), "customer": list(self.customer),
            "start_time": self.start_time, "status": self.status,
            "rider_id": self.rider_id, "accept_time": self.accept_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken, "active_ticks": self.active_ticks,
            "distance": self.distance, "fee": self.fee,
            "efficiency": self.efficiency,
        }

    @classmethod
    def from_dict(cls, data):
        order = cls(tuple(data["raw_restaurant"]), tuple(data["raw_customer"]),
                    start_time=data.get("start_time", 0), order_id=data["id"])
        for key in ("status", "rider_id", "accept_time", "pickup_time",
                    "completion_time", "time_taken", "active_ticks", "fee",
                    "efficiency"):
            if key in data:
                setattr(order, key, data[key])
        return order

    def __repr__(self):
        return "Order(#%d %s->%s %s)" % (self.id, self.restaurant,
                                         self.customer, self.status)
