"""Order data model and coordinate conversion helpers."""

import logging

import config
import globalvar

logger = logging.getLogger(__name__)


def clamp_coordinate(value):
    """Clamp a coordinate into the drawable range 0..799.

    Args:
        value: Numeric coordinate.

    Returns:
        Integer coordinate inside the first 800-unit cell range.
    """
    return min(max(int(value), 0), config.MAP_SIZE - 1)


def to_cell_center(value):
    """Convert a coordinate to the centre of its 100-unit grid cell.

    Uses ``center = (value // 100) * 100 + 50``.

    Args:
        value: Coordinate in the range 0-800.

    Returns:
        Integer cell-centre coordinate.
    """
    cell = config.CELL_SIZE
    clamped = clamp_coordinate(value)
    return (clamped // cell) * cell + cell // 2


def to_cell_center_point(point):
    """Convert an ``(x, y)`` point to its grid cell centre.

    Args:
        point: ``(x, y)`` tuple.

    Returns:
        ``(x, y)`` tuple of cell-centre coordinates.
    """
    return (to_cell_center(point[0]), to_cell_center(point[1]))


def _next_order_id():
    """Return the next unique order ID and store the counter."""
    counter = (globalvar.get_value("order_counter") or 0) + 1
    globalvar.set_value("order_counter", counter)
    return counter


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        res_pos: Restaurant cell-centre ``(x, y)``.
        cus_pos: Customer cell-centre ``(x, y)``.
        status: One of ``created``, ``assigned``, ``picking_up``,
            ``delivering``, or ``completed``.
        rider_id: ID of the assigned rider, or None.
        start_tick: Tick at which the order was created.
        complete_tick: Tick at which the order was delivered, or None.
        time_taken: Ticks from creation to delivery, or None.
        distance: Manhattan distance between restaurant and customer.
        efficiency: Distance units covered per tick on completion, or None.
    """

    STATUS_CREATED = "created"
    STATUS_ASSIGNED = "assigned"
    STATUS_PICKING_UP = "picking_up"
    STATUS_DELIVERING = "delivering"
    STATUS_COMPLETED = "completed"

    def __init__(self, res_pos, cus_pos):
        """Create an order and convert its coordinates to grid cell centres.

        Args:
            res_pos: Restaurant ``(x, y)`` in the range 0-800.
            cus_pos: Customer ``(x, y)`` in the range 0-800.
        """
        self.id = _next_order_id()
        self.res_pos = to_cell_center_point(res_pos)
        self.cus_pos = to_cell_center_point(cus_pos)
        self.status = self.STATUS_CREATED
        self.rider_id = None
        self.start_tick = globalvar.get_value("tick", 0) or 0
        self.complete_tick = None
        self.time_taken = None
        self.distance = abs(self.res_pos[0] - self.cus_pos[0]) + abs(
            self.res_pos[1] - self.cus_pos[1]
        )
        self.efficiency = None
        logger.debug("Created order %d", self.id)

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider.

        Args:
            rider_id: ID of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = self.STATUS_ASSIGNED

    def mark_picking_up(self):
        """Mark the order as being picked up."""
        self.status = self.STATUS_PICKING_UP

    def mark_delivering(self):
        """Mark the order as out for delivery."""
        self.status = self.STATUS_DELIVERING

    def complete(self, tick):
        """Mark the order as delivered and record completion metrics.

        Args:
            tick: Simulated tick of delivery.
        """
        self.status = self.STATUS_COMPLETED
        self.complete_tick = tick
        self.time_taken = max(tick - self.start_tick, 0)
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 2)
        else:
            self.efficiency = float(self.distance)
        logger.info(
            "Order %d completed in %d ticks (efficiency %s)",
            self.id,
            self.time_taken,
            self.efficiency,
        )

    def to_dict(self):
        """Return a JSON-serialisable representation of the order.

        Returns:
            Dictionary with all order attributes.
        """
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_tick": self.start_tick,
            "complete_tick": self.complete_tick,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "efficiency": self.efficiency,
        }

    def __repr__(self):
        return f"Order(id={self.id}, status={self.status}, rider={self.rider_id})"
