"""Order data model."""

import globalvar
from path_planner import PathPlanner, manhattan


class Order:
    """A delivery order from a restaurant to a customer.

    Attributes:
        id: unique order number.
        raw: the raw user input ``[rx, ry, cx, cy]``.
        res_pos / cus_pos: converted grid-centre positions.
        status: "pending", "assigned", "picked_up" or "completed".
        rider_id: id of the assigned rider (or None).
        start_time / assign_time / accept_time / pickup_time /
        complete_time: simulation ticks of the lifecycle events.
        distance: Manhattan distance restaurant -> customer.
        route_distance: street route length restaurant -> customer.
        travel_distance: distance actually travelled by the rider.
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        self.id = Order._next_id
        Order._next_id += 1
        self.raw = [int(res_pos[0]), int(res_pos[1]),
                    int(cus_pos[0]), int(cus_pos[1])]
        self.res_pos = PathPlanner.to_center_point(res_pos)
        self.cus_pos = PathPlanner.to_center_point(cus_pos)
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("time", 0)
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.distance = manhattan(self.res_pos, self.cus_pos)
        planner = PathPlanner()
        self.route_distance = planner.path_length(
            self.res_pos, planner.plan(self.res_pos, self.cus_pos))
        self.travel_distance = 0

    def assign_to(self, rider_id):
        """Assign the order to the rider with ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assign_time = globalvar.get_value("time", 0)

    def mark_picked_up(self, time):
        """Record the pickup at the restaurant."""
        self.status = "picked_up"
        self.pickup_time = time

    def mark_completed(self, time):
        """Record the delivery to the customer."""
        self.status = "completed"
        self.complete_time = time

    @property
    def time_taken(self):
        """Ticks from creation to completion (None if not completed)."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.start_time

    @property
    def efficiency(self):
        """Route distance / travelled distance ratio (1.0 is ideal)."""
        if self.status != "completed" or not self.travel_distance:
            return None
        total = self.route_distance + 0.0
        return round(total / self.travel_distance, 3) if total else None

    def to_dict(self):
        """Serialisable representation."""
        return {
            "id": self.id,
            "raw": self.raw,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "assign_time": self.assign_time,
            "accept_time": self.accept_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
            "route_distance": self.route_distance,
            "travel_distance": self.travel_distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self):
        return (f"Order(id={self.id}, res={self.res_pos}, "
                f"cus={self.cus_pos}, status={self.status})")
