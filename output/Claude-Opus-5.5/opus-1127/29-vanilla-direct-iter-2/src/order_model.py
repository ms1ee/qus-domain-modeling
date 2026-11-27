"""Order data model."""

import globalvar
from path_planner import PathPlanner


def _now():
    t = globalvar.get_value("time")
    return t if isinstance(t, int) else 0


class Order:
    """A delivery order from a restaurant to a customer.

    Attributes:
        id: unique order id.
        res_pos / cus_pos: grid-centre coordinates of restaurant / customer.
        raw: original input ``[rx, ry, cx, cy]``.
        status: "pending", "assigned", "picking_up", "delivering", "completed".
        rider_id: id of the assigned rider (or None).
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        self.id = Order._next_id
        Order._next_id += 1
        self.raw = [int(res_pos[0]), int(res_pos[1]),
                    int(cus_pos[0]), int(cus_pos[1])]
        self.res_pos = PathPlanner.to_grid_center(res_pos[0], res_pos[1])
        self.cus_pos = PathPlanner.to_grid_center(cus_pos[0], cus_pos[1])
        self.status = "pending"
        self.rider_id = None
        self.created_at = _now()
        self.assigned_at = None
        self.accepted_at = None
        self.picked_up_at = None
        self.completed_at = None
        self.new_rider_added = False
        self.distance = PathPlanner.route_distance(self.res_pos, self.cus_pos)

    @classmethod
    def reset_counter(cls):
        """Reset the order id counter (used on system initialisation)."""
        cls._next_id = 1

    def assign_to(self, rider_id):
        """Record the assignment of this order to ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assigned_at = _now()

    @property
    def time_taken(self):
        """Ticks from creation to completion (None if not completed)."""
        if self.completed_at is None:
            return None
        return self.completed_at - self.created_at

    @property
    def efficiency(self):
        """Delivery efficiency: restaurant->customer distance per tick."""
        t = self.time_taken
        if not t:
            return None
        return round(self.distance / t, 2)

    def to_list(self):
        """Order in the ``[rx, ry, cx, cy]`` (grid centre) format."""
        return [self.res_pos[0], self.res_pos[1], self.cus_pos[0], self.cus_pos[1]]

    def to_dict(self):
        """JSON-serialisable representation."""
        return {
            "id": self.id,
            "raw": self.raw,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_at": self.created_at,
            "assigned_at": self.assigned_at,
            "picked_up_at": self.picked_up_at,
            "completed_at": self.completed_at,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }

    def __repr__(self):
        return "Order(id=%d, %s->%s, %s)" % (self.id, self.res_pos,
                                            self.cus_pos, self.status)
