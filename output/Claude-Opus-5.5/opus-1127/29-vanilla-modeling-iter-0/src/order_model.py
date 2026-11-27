"""Order data model."""

import globalvar
from path_planner import PathPlanner


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are automatically converted to grid-cell centres.

    Attributes:
        id: unique order id.
        res_pos / cus_pos: restaurant and customer positions (cell centres).
        status: "pending", "assigned", "picking_up", "delivering", "completed".
        rider_id: id of the assigned rider or None.
        start_time, pickup_time, completion_time, time_taken: tick values.
        distance: Euclidean distance restaurant -> customer.
        travel_distance: distance actually travelled by the rider.
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        self.id = Order._next_id
        Order._next_id += 1
        self.res_pos = PathPlanner.to_cell_center(res_pos[0], res_pos[1])
        self.cus_pos = PathPlanner.to_cell_center(cus_pos[0], cus_pos[1])
        self.raw_input = [int(res_pos[0]), int(res_pos[1]),
                          int(cus_pos[0]), int(cus_pos[1])]
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0)
        self.assign_time = None
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.distance = round(PathPlanner.euclidean(self.res_pos,
                                                    self.cus_pos), 2)
        self.travel_distance = 0

    @classmethod
    def reset_counter(cls):
        """Reset the order id counter (used on system init)."""
        cls._next_id = 1

    def assign_to(self, rider_id):
        """Record the assignment of this order to rider ``rider_id``."""
        self.rider_id = rider_id
        self.assign_time = globalvar.get_value("tick", 0)
        if self.status == "pending":
            self.status = "assigned"

    def to_list(self):
        """Return the order as [restaurant_x, restaurant_y, customer_x, customer_y]."""
        return [self.res_pos[0], self.res_pos[1],
                self.cus_pos[0], self.cus_pos[1]]

    def to_dict(self):
        """Serialisable representation."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "assign_time": self.assign_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "travel_distance": self.travel_distance,
        }

    def __repr__(self):
        return "Order(id=%d, res=%s, cus=%s, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
