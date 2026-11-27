"""Order data model.

An order is described by ``[restaurant_x, restaurant_y, customer_x,
customer_y]`` with coordinates in the range 0-800. Coordinates are snapped to
the top-left corner of their grid cell, which is also a street intersection.
"""

import globalvar
from path_planner import CELL_SIZE, MAP_SIZE

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def snap_to_grid(value):
    """Convert a coordinate to the top-left corner of its grid cell.

    Args:
        value: Integer coordinate (values are clamped to 0-800).

    Returns:
        Integer multiple of 100 in the range 0-800.
    """
    clamped = max(0, min(int(value), MAP_SIZE))
    return (clamped // CELL_SIZE) * CELL_SIZE


class Order:
    """A food delivery order from a restaurant to a customer."""

    _id_counter = 0

    def __init__(self, res_pos, cus_pos):
        """Create an order and snap its coordinates to the grid.

        Args:
            res_pos: Restaurant position as (x, y) in 0-800.
            cus_pos: Customer position as (x, y) in 0-800.
        """
        Order._id_counter += 1
        self.id = Order._id_counter
        self.restaurant_x = snap_to_grid(res_pos[0])
        self.restaurant_y = snap_to_grid(res_pos[1])
        self.customer_x = snap_to_grid(cus_pos[0])
        self.customer_y = snap_to_grid(cus_pos[1])
        self.status = STATUS_PENDING
        self.rider_id = None
        self.start_time = globalvar.current_tick()
        self.completion_time = None
        self.distance = (abs(self.customer_x - self.restaurant_x)
                         + abs(self.customer_y - self.restaurant_y))
        self.time_taken = None

    def assign_to(self, rider_id):
        """Record the rider responsible for this order."""
        self.rider_id = rider_id
        if self.status == STATUS_PENDING:
            self.status = STATUS_ASSIGNED

    def complete(self, tick):
        """Mark the order delivered and record completion statistics.

        Args:
            tick: Simulated tick at which delivery finished.
        """
        self.status = STATUS_COMPLETED
        self.completion_time = tick
        self.time_taken = tick - self.start_time

    def efficiency(self):
        """Return delivery distance per tick, or None if not completed."""
        if not self.time_taken:
            return None
        return self.distance / self.time_taken

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": [self.restaurant_x, self.restaurant_y],
            "customer": [self.customer_x, self.customer_y],
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
