"""Order data model: coordinates, lifecycle status and delivery metrics."""

import itertools
import logging

import globalvar
from path_planner import to_cell_center

logger = logging.getLogger(__name__)

DELIVERY_FEE = 300
_ORDER_IDS = itertools.count(1)


def _current_tick():
    """Return the current simulated tick from the global store."""
    return globalvar.get_value("tick") or 0


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant location as grid cell center ``(x, y)``.
        cus_pos: Customer location as grid cell center ``(x, y)``.
        status: One of ``"pending"``, ``"assigned"``, ``"picking_up"``,
            ``"delivering"``, ``"completed"``.
        rider_id: Id of the assigned rider or None.
        start_time: Tick when the order was created.
        pickup_time: Tick when the rider reached the restaurant.
        finish_time: Tick when the order was delivered.
        distance: Distance travelled by the rider while carrying the order.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order and convert its coordinates to cell centers.

        Args:
            res_pos: Restaurant coordinates ``(x, y)`` in 0-800.
            cus_pos: Customer coordinates ``(x, y)`` in 0-800.
        """
        self.id = next(_ORDER_IDS)
        self.res_pos = to_cell_center(int(res_pos[0]), int(res_pos[1]))
        self.cus_pos = to_cell_center(int(cus_pos[0]), int(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = _current_tick()
        self.pickup_time = None
        self.finish_time = None
        self.distance = 0

    def assign_to(self, rider_id):
        """Record the rider this order was assigned to.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"

    def mark_completed(self, finish_tick):
        """Mark the order as delivered and record completion data.

        Args:
            finish_tick: Simulated tick of delivery.

        Returns:
            Delivery fee earned for the order.
        """
        self.status = "completed"
        self.finish_time = finish_tick
        logger.info("Order %s completed at tick %s", self.id, finish_tick)
        return DELIVERY_FEE

    @property
    def time_taken(self):
        """Ticks elapsed from creation to delivery, or None if unfinished."""
        if self.finish_time is None:
            return None
        return self.finish_time - self.start_time

    def efficiency(self):
        """Return distance units covered per tick, or None if unavailable."""
        taken = self.time_taken
        if not taken:
            return None
        return round(self.distance / taken, 2)

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "finish_time": self.finish_time,
            "distance": self.distance,
        }
