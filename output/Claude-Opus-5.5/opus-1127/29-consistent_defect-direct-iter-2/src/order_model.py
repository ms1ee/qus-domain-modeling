"""Order data model."""

import globalvar

MAP_SIZE = 800
CELL = 100


def to_grid_corner(v):
    """Convert a coordinate to the top-left corner of its grid cell."""
    v = max(0, min(MAP_SIZE, int(v)))
    return min((v // CELL) * CELL, MAP_SIZE - CELL)


def to_grid_center(v):
    """Convert a coordinate to its grid cell center."""
    return to_grid_corner(v) + CELL // 2


class Order:
    """A delivery order from a restaurant to a customer."""

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        self.id = Order._next_id
        Order._next_id += 1
        self.res_pos = tuple(int(v) for v in res_pos)
        self.cus_pos = tuple(int(v) for v in cus_pos)
        self.res_grid = (to_grid_corner(self.res_pos[0]), to_grid_corner(self.res_pos[1]))
        self.cus_grid = (to_grid_corner(self.cus_pos[0]), to_grid_corner(self.cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        t = globalvar.get_value("time")
        self.create_time = t if t is not None else 0
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Record the rider this order is assigned to."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"

    def time_taken(self):
        """Ticks from creation to completion, or None."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.create_time

    def to_dict(self):
        """Serialisable representation."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "create_time": self.create_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
            "time_taken": self.time_taken(),
        }
