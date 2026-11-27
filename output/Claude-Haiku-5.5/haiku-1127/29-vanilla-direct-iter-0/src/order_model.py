"""Order data model with coordinate normalisation and lifecycle tracking."""

import math

from globalvar import get_value
from grid import to_cell_center


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order number.
        res_pos: Restaurant grid-cell centre (x, y).
        cus_pos: Customer grid-cell centre (x, y).
        status: "pending", "assigned", "picking_up", "delivering" or
            "completed".
        rider_id: Identifier of the assigned rider, or None.
        start_time: Tick at which the order was created.
        completion_time: Tick at which delivery finished, or None.
        time_taken: Ticks between creation and completion, or None.
        distance: Euclidean distance between restaurant and customer.
        efficiency: distance / time_taken (units per tick), or None.
    """

    _id_counter = 0

    def __init__(self, res_pos, cus_pos) -> None:
        """Create an order and convert its coordinates to cell centres.

        Args:
            res_pos: Raw restaurant coordinate (x, y), range 0-800.
            cus_pos: Raw customer coordinate (x, y), range 0-800.
        """
        Order._id_counter += 1
        self.id = Order._id_counter
        self.res_pos = to_cell_center(res_pos[0], res_pos[1])
        self.cus_pos = to_cell_center(cus_pos[0], cus_pos[1])
        self.status = "pending"
        self.rider_id = None
        self.start_time = int(get_value("tick", 0))
        self.completion_time = None
        self.time_taken = None
        self.distance = round(math.hypot(
            self.cus_pos[0] - self.res_pos[0],
            self.cus_pos[1] - self.res_pos[1]), 2)
        self.efficiency = None

    def assign_to(self, rider_id: int) -> None:
        """Record that the order has been assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = "assigned"

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and compute delivery efficiency.

        Args:
            tick: The simulated tick at which delivery finished.
        """
        self.status = "completed"
        self.completion_time = tick
        self.time_taken = max(0, tick - self.start_time)
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 2)
        else:
            self.efficiency = round(self.distance, 2)

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "efficiency": self.efficiency,
        }
