"""Order data model."""

import math

import globalvar
from gridmap import to_cell_center


class OrderStatus:
    """Order lifecycle statuses."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    PICKING_UP = "picking_up"
    DELIVERING = "delivering"
    COMPLETED = "completed"


def _next_order_id():
    counter = globalvar.get_value("order_id_counter", 0) or 0
    counter += 1
    globalvar.set_value("order_id_counter", counter)
    return counter


def _unpack(pos):
    try:
        x, y = pos[0], pos[1]
    except (TypeError, IndexError, KeyError):
        raise ValueError("Position must be a pair of coordinates: {!r}".format(pos))
    return x, y


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are converted to the centre of their grid cells.
    """

    def __init__(self, res_pos, cus_pos, start_time=None, order_id=None):
        rx, ry = _unpack(res_pos)
        cx, cy = _unpack(cus_pos)
        self.raw = [rx, ry, cx, cy]
        self.res_x = to_cell_center(rx)
        self.res_y = to_cell_center(ry)
        self.cus_x = to_cell_center(cx)
        self.cus_y = to_cell_center(cy)
        if order_id is None:
            self.id = _next_order_id()
        else:
            self.id = int(order_id)
            if self.id > (globalvar.get_value("order_id_counter", 0) or 0):
                globalvar.set_value("order_id_counter", self.id)
        self.start_time = (globalvar.get_value("tick", 0) or 0) if start_time is None else start_time
        self.assign_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.distance = round(math.hypot(self.cus_x - self.res_x, self.cus_y - self.res_y), 2)
        self.rider_id = None
        self.status = OrderStatus.PENDING

    @property
    def order_id(self):
        """Alias for :attr:`id`."""
        return self.id

    @property
    def res_pos(self):
        """Restaurant position (grid cell centre)."""
        return (self.res_x, self.res_y)

    @property
    def cus_pos(self):
        """Customer position (grid cell centre)."""
        return (self.cus_x, self.cus_y)

    def as_list(self):
        """Return ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.res_x, self.res_y, self.cus_x, self.cus_y]

    def assign_to(self, rider_id):
        """Assign this order to the rider identified by ``rider_id``."""
        self.rider_id = rider_id
        if self.status == OrderStatus.PENDING:
            self.status = OrderStatus.ASSIGNED
        if self.assign_time is None:
            self.assign_time = globalvar.get_value("tick", 0) or 0

    def mark_picking_up(self):
        """Mark that the rider is heading to the restaurant."""
        if self.status in (OrderStatus.PENDING, OrderStatus.ASSIGNED):
            self.status = OrderStatus.PICKING_UP

    def mark_picked_up(self, tick):
        """Mark that the food has been picked up."""
        self.pickup_time = tick
        self.status = OrderStatus.DELIVERING

    def mark_completed(self, tick):
        """Mark the order as delivered."""
        self.completion_time = tick
        self.time_taken = tick - (self.start_time or 0)
        self.status = OrderStatus.COMPLETED

    def is_completed(self):
        """Return True when the order has been delivered."""
        return self.status == OrderStatus.COMPLETED

    def to_dict(self):
        """Serialise the order to a JSON compatible dict."""
        return {
            "id": self.id,
            "raw": list(self.raw),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "start_time": self.start_time,
            "assign_time": self.assign_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "rider_id": self.rider_id,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from :meth:`to_dict` output."""
        order = cls(data["res_pos"], data["cus_pos"],
                    start_time=data.get("start_time", 0), order_id=data["id"])
        order.raw = list(data.get("raw", order.as_list()))
        order.assign_time = data.get("assign_time")
        order.pickup_time = data.get("pickup_time")
        order.completion_time = data.get("completion_time")
        order.time_taken = data.get("time_taken")
        order.rider_id = data.get("rider_id")
        order.status = data.get("status", OrderStatus.PENDING)
        return order

    def __repr__(self):
        return "Order(id={}, res={}, cus={}, status={}, rider={})".format(
            self.id, self.res_pos, self.cus_pos, self.status, self.rider_id)
