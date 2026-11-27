"""Order data model.

An order is described by ``[restaurant_x, restaurant_y, customer_x, customer_y]``.
Locations are converted to the top-left corner of their grid cell on creation.

Order status values:
    "pending"      created, not yet assigned to a rider
    "assigned"     assigned to a rider, not yet accepted
    "accepted"     accepted by the rider, waiting for pickup
    "picking_up"   rider is travelling to the restaurant
    "delivering"   food picked up, rider is travelling to the customer
    "completed"    delivered to the customer
"""

import itertools

import globalvar
from path_planner import PathPlanner, to_cell_corner

_planner = PathPlanner()


class Order:
    """A food delivery order.

    Attributes:
        id (int): Unique order identifier.
        res_pos (tuple[int, int]): Restaurant location (grid cell corner).
        cus_pos (tuple[int, int]): Customer location (grid cell corner).
        status (str): Lifecycle status, see module docstring.
        rider_id (int | None): ID of the assigned rider.
        start_time (int): Tick at which the order was created.
        distance (float): Manhattan distance restaurant to customer.
        time_taken (int | None): Ticks from creation to completion.
        completion_time (int | None): Tick at which delivery completed.
    """

    _id_sequence = itertools.count(1)

    def __init__(self, res_pos, cus_pos):
        """Create an order and convert its locations to grid cell corners.

        Args:
            res_pos: ``(x, y)`` restaurant coordinates.
            cus_pos: ``(x, y)`` customer coordinates.
        """
        self.id = next(Order._id_sequence)
        self.res_pos = to_cell_corner(*res_pos)
        self.cus_pos = to_cell_corner(*cus_pos)
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("current_tick", 0)
        self.distance = float(
            _planner.route_length(_planner.plan_route(self.res_pos, self.cus_pos))
        )
        self.time_taken = None
        self.completion_time = None

    def assign_to(self, rider_id):
        """Record the assigned rider and mark the order as assigned.

        Args:
            rider_id: ID of the rider receiving the order.
        """
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"

    def complete(self, tick):
        """Mark the order as delivered and record timing data.

        Args:
            tick: Simulation tick at which delivery finished.
        """
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = tick - self.start_time

    def efficiency(self):
        """Return distance covered per tick, or None if not yet completed."""
        if not self.time_taken:
            return None
        return self.distance / self.time_taken

    def to_list(self):
        """Return the order as ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.res_pos[0], self.res_pos[1], self.cus_pos[0], self.cus_pos[1]]

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "completion_time": self.completion_time,
        }
