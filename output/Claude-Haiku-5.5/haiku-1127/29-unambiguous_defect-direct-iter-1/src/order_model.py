"""Order data model.

An order is described by restaurant and customer positions, both snapped to
street intersections, plus lifecycle information (status and timestamps).
"""

import itertools

import globalvar
from path_planner import manhattan, to_lattice_point

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKED_UP = "picked_up"
STATUS_COMPLETED = "completed"

_ORDER_IDS = itertools.count(1)


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant ``(x, y)`` on a street intersection.
        cus_pos: Customer ``(x, y)`` on a street intersection.
        status: One of "pending", "assigned", "picked_up", "completed".
        rider_id: Id of the assigned rider, or None.
        created_tick: Simulated time when the order was created.
        picked_up_tick: Time of pickup, or None.
        completed_tick: Time of delivery, or None.
    """

    def __init__(self, res_pos, cus_pos):
        """Create a pending order.

        Args:
            res_pos: Restaurant ``(x, y)``; snapped to the nearest intersection.
            cus_pos: Customer ``(x, y)``; snapped to the nearest intersection.
        """
        self.id = next(_ORDER_IDS)
        self.res_pos = to_lattice_point(res_pos)
        self.cus_pos = to_lattice_point(cus_pos)
        self.status = STATUS_PENDING
        self.rider_id = None
        self.created_tick = globalvar.get_value("tick", 0)
        self.picked_up_tick = None
        self.completed_tick = None

    @property
    def distance(self):
        """Return the Manhattan distance from restaurant to customer."""
        return manhattan(self.res_pos, self.cus_pos)

    @property
    def time_taken(self):
        """Return ticks from creation to completion, or None if unfinished."""
        if self.completed_tick is None:
            return None
        return self.completed_tick - self.created_tick

    @property
    def efficiency(self):
        """Return delivery efficiency as distance per tick, or None."""
        taken = self.time_taken
        if not taken:
            return None
        return round(self.distance / taken, 2)

    def assign_to(self, rider_id):
        """Record the assigned rider and mark the order as assigned.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_picked_up(self, tick):
        """Mark the order as picked up from the restaurant.

        Args:
            tick: Simulated time of pickup.
        """
        self.picked_up_tick = tick
        self.status = STATUS_PICKED_UP

    def complete(self, tick):
        """Mark the order as delivered.

        Args:
            tick: Simulated time of delivery.
        """
        self.completed_tick = tick
        self.status = STATUS_COMPLETED

    def is_completed(self):
        """Return True once the order has been delivered."""
        return self.status == STATUS_COMPLETED

    def to_dict(self):
        """Return a JSON-serialisable representation of the order.

        Returns:
            dict: Order attributes.
        """
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_tick": self.created_tick,
            "picked_up_tick": self.picked_up_tick,
            "completed_tick": self.completed_tick,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
