"""Order data model."""

import globalvar
from grid_map import DEFAULT_GRID


def to_grid(value):
    """Convert a raw coordinate to the top-left corner of its grid cell."""
    return DEFAULT_GRID.to_cell_corner(value)


def _next_order_id():
    counter = globalvar.get_value("order_id_counter")
    if not isinstance(counter, int):
        counter = 0
    counter += 1
    globalvar.set_value("order_id_counter", counter)
    return counter


def _now():
    tick = globalvar.get_value("tick")
    return tick if isinstance(tick, int) else 0


class Order:
    """A delivery order from a restaurant to a customer."""

    def __init__(self, res_pos, cus_pos):
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("positions must be (x, y) pairs")
        self.id = _next_order_id()
        self.raw = [int(res_pos[0]), int(res_pos[1]),
                    int(cus_pos[0]), int(cus_pos[1])]
        self.res_x = to_grid(res_pos[0])
        self.res_y = to_grid(res_pos[1])
        self.cus_x = to_grid(cus_pos[0])
        self.cus_y = to_grid(cus_pos[1])
        self.res_pos = (self.res_x, self.res_y)
        self.cus_pos = (self.cus_x, self.cus_y)
        self.status = "pending"
        self.rider_id = None
        self.start_time = _now()
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.distance = abs(self.res_x - self.cus_x) + abs(self.res_y - self.cus_y)

    def assign_to(self, rider_id):
        """Record that this order is assigned to ``rider_id``."""
        self.rider_id = rider_id
        self.assign_time = _now()
        if self.status == "pending":
            self.status = "assigned"

    def mark_accepted(self, time):
        """Rider started heading to the restaurant."""
        self.accept_time = time
        if self.status != "completed":
            self.status = "picking_up"

    def mark_picked_up(self, time):
        """Rider arrived at the restaurant."""
        self.pickup_time = time
        if self.status != "completed":
            self.status = "delivering"

    def mark_completed(self, time):
        """Rider delivered the order."""
        self.completion_time = time
        self.time_taken = time - self.start_time
        self.status = "completed"

    def efficiency(self):
        """Distance delivered per tick (None if not completed)."""
        if not self.time_taken:
            return None
        return round(self.distance / self.time_taken, 2)

    def to_list(self):
        """Return ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.res_x, self.res_y, self.cus_x, self.cus_y]

    def to_dict(self):
        """Serialisable representation."""
        return {
            "id": self.id,
            "raw": self.raw,
            "order": self.to_list(),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
        }

    def __repr__(self):
        return "Order(id=%d, %s, status=%s)" % (self.id, self.to_list(), self.status)
