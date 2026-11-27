"""Order data model.

An order holds the restaurant and customer positions as entered by the user
(0-800 units) and the grid cell centers they are converted to.
"""

import itertools

import globalvar
import grid

PENDING = "pending"
ASSIGNED = "assigned"
PICKING_UP = "picking_up"
DELIVERING = "delivering"
COMPLETED = "completed"

_id_sequence = itertools.count(1)


def _parse_position(pos, label):
    """Validate an ``(x, y)`` pair of integer coordinates.

    Args:
        pos: Sequence of two values.
        label: Human-readable name used in error messages.

    Returns:
        tuple[int, int]: Validated coordinates.

    Raises:
        ValueError: If the pair is malformed or out of range.
    """
    try:
        x, y = pos
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} position must be a pair (x, y)") from exc
    return (grid.validate_coordinate(x), grid.validate_coordinate(y))


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        restaurant_pos: Restaurant coordinates as entered (0-800).
        customer_pos: Customer coordinates as entered (0-800).
        res_grid: Restaurant grid cell center.
        cus_grid: Customer grid cell center.
        status: One of pending, assigned, picking_up, delivering, completed.
        rider_id: Identifier of the assigned rider, or None.
        start_tick: Simulation tick at which the order was created.
        complete_tick: Simulation tick of delivery, or None.
        distance: Accumulated planned travel distance in units.
        settled: True once the order's revenue has been booked.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order from raw coordinates.

        Args:
            res_pos: Restaurant position ``(x, y)`` in 0-800.
            cus_pos: Customer position ``(x, y)`` in 0-800.

        Raises:
            ValueError: If a coordinate is invalid or out of range.
            TypeError: If a coordinate is not an integer.
        """
        self.id = next(_id_sequence)
        self.restaurant_pos = _parse_position(res_pos, "restaurant")
        self.customer_pos = _parse_position(cus_pos, "customer")
        self.res_grid = grid.cell_center(*self.restaurant_pos)
        self.cus_grid = grid.cell_center(*self.customer_pos)
        self.status = PENDING
        self.rider_id = None
        self.start_tick = globalvar.get_value("tick", 0)
        self.complete_tick = None
        self.distance = 0
        self.settled = False

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = ASSIGNED

    def complete(self, tick):
        """Mark the order as delivered.

        Args:
            tick: Simulation tick at which delivery finished.
        """
        self.status = COMPLETED
        self.complete_tick = tick

    @property
    def time_taken(self):
        """Ticks from creation to delivery, or None if not completed."""
        if self.complete_tick is None:
            return None
        return self.complete_tick - self.start_tick

    @property
    def efficiency(self):
        """Distance covered per tick, or None if not completed."""
        taken = self.time_taken
        if not taken:
            return None
        return self.distance / taken

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant_pos": list(self.restaurant_pos),
            "customer_pos": list(self.customer_pos),
            "res_grid": list(self.res_grid),
            "cus_grid": list(self.cus_grid),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_tick": self.start_tick,
            "complete_tick": self.complete_tick,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "settled": self.settled,
        }
