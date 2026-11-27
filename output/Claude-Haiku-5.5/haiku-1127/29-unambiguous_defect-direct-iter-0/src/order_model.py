"""Order data model: coordinate validation, grid snapping and order records."""

import itertools

from globalvar import get_value
from path_planner import MAP_SIZE, PathPlanner


def validate_coordinate(value):
    """Validate that a coordinate is an integer within 0..800.

    Args:
        value: Candidate coordinate.

    Returns:
        The validated integer.

    Raises:
        ValueError: If the value is not an integer or is out of range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"coordinate {value!r} is not an integer")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"coordinate {value} out of range 0-{MAP_SIZE}")
    return value


def to_grid_center(value):
    """Convert a validated coordinate to its grid cell centre.

    Args:
        value: Integer coordinate in range.

    Returns:
        Cell-centre coordinate (``(value // 100) * 100 + 50``, clamped).
    """
    return PathPlanner.cell_center(value)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique positive integer order identifier.
        res_pos: Restaurant grid-centre tuple ``(x, y)``.
        cus_pos: Customer grid-centre tuple ``(x, y)``.
        status: One of ``created``, ``assigned``, ``picking_up``,
            ``delivering``, ``completed``, ``unassigned``.
        rider_id: ID of the assigned rider, or None.
        created_tick: Simulated time of creation.
        accepted_tick: Tick when the rider started pickup, or None.
        pickup_tick: Tick when the rider reached the restaurant, or None.
        completed_tick: Tick of delivery completion, or None.
        distance: Street distance from restaurant to customer.
        travelled: Total distance travelled by the rider for this order.
    """

    _ids = itertools.count(1)

    def __init__(self, res_pos, cus_pos):
        """Create an order and snap both locations to grid centres.

        Args:
            res_pos: Sequence ``(x, y)`` of raw restaurant coordinates (0-800).
            cus_pos: Sequence ``(x, y)`` of raw customer coordinates (0-800).

        Raises:
            ValueError: If any coordinate is invalid.
        """
        rx = validate_coordinate(res_pos[0])
        ry = validate_coordinate(res_pos[1])
        cx = validate_coordinate(cus_pos[0])
        cy = validate_coordinate(cus_pos[1])
        self.id = next(Order._ids)
        self.res_pos = (to_grid_center(rx), to_grid_center(ry))
        self.cus_pos = (to_grid_center(cx), to_grid_center(cy))
        self.status = "created"
        self.rider_id = None
        self.created_tick = get_value("tick", 0)
        self.accepted_tick = None
        self.pickup_tick = None
        self.completed_tick = None
        self.distance = PathPlanner.manhattan(self.res_pos, self.cus_pos)
        self.travelled = 0

    def assign_to(self, rider_id):
        """Record the rider this order is assigned to.

        Args:
            rider_id: Integer ID of the assigned rider.
        """
        self.rider_id = rider_id
        if self.status == "created":
            self.status = "assigned"

    def complete(self, tick):
        """Mark the order as delivered.

        Args:
            tick: Simulated time of completion.
        """
        self.status = "completed"
        self.completed_tick = tick

    def time_taken(self):
        """Return ticks from creation to completion.

        Returns:
            Integer ticks, or None if the order is not yet completed.
        """
        if self.completed_tick is None:
            return None
        return self.completed_tick - self.created_tick

    def efficiency(self):
        """Return delivery efficiency as distance per tick.

        Returns:
            Float efficiency, or 0.0 when the order is not completed.
        """
        taken = self.time_taken()
        if not taken:
            return 0.0
        return round(self.distance / taken, 2)

    def to_dict(self):
        """Serialise the order to a JSON-compatible dictionary.

        Returns:
            Dictionary describing the order.
        """
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_tick": self.created_tick,
            "accepted_tick": self.accepted_tick,
            "pickup_tick": self.pickup_tick,
            "completed_tick": self.completed_tick,
            "distance": self.distance,
            "travelled": self.travelled,
        }
