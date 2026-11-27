"""Order data model: coordinates, lifecycle status and delivery statistics."""

import globalvar
import grid


def _validate_point(point, label):
    """Validate an [x, y] position and return it as a tuple of ints.

    Args:
        point: Sequence of two integers in the range 0-800.
        label: Name used in error messages.

    Returns:
        tuple[int, int]: Validated (x, y).

    Raises:
        ValueError: If the point is malformed or out of range.
    """
    try:
        x, y = point
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} position must be [x, y].") from exc
    for value in (x, y):
        if not grid.is_valid_coordinate(value):
            raise ValueError(
                f"{label} coordinate {value} is invalid; "
                "coordinates must be integers in the range 0-800.")
    return (x, y)


def _next_order_id():
    """Return the next unique order identifier."""
    counter = globalvar.get_value("order_id_counter", 0) + 1
    globalvar.set_value("order_id_counter", counter)
    return counter


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        res_pos: Raw restaurant position as entered by the user.
        cus_pos: Raw customer position as entered by the user.
        res_grid: Restaurant position converted to grid cell center.
        cus_grid: Customer position converted to grid cell center.
        status: "created", "assigned", "picking_up", "delivering" or
            "completed".
        rider_id: Identifier of the assigned rider, or None.
        start_time: Tick at which the order was created.
        completion_time: Tick at which delivery finished, or None.
        time_taken: Ticks from creation to completion, or None.
        distance: Manhattan distance restaurant → customer in units.
        efficiency: Distance per tick (units/tick), or None.
        route: Sequence of (x, y) positions travelled for this order.
    """

    STATUS_CREATED = "created"
    STATUS_ASSIGNED = "assigned"
    STATUS_PICKING_UP = "picking_up"
    STATUS_DELIVERING = "delivering"
    STATUS_COMPLETED = "completed"

    def __init__(self, res_pos, cus_pos):
        """Create an order from restaurant and customer positions.

        Args:
            res_pos: [x, y] restaurant position (0-800).
            cus_pos: [x, y] customer position (0-800).

        Raises:
            ValueError: If any coordinate is invalid.
        """
        self.res_pos = _validate_point(res_pos, "Restaurant")
        self.cus_pos = _validate_point(cus_pos, "Customer")
        self.id = _next_order_id()
        self.res_grid = grid.to_grid_point(*self.res_pos)
        self.cus_grid = grid.to_grid_point(*self.cus_pos)
        self.status = self.STATUS_CREATED
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0)
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.distance = grid.manhattan(self.res_grid, self.cus_grid)
        self.efficiency = None
        self.route = []

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = self.STATUS_ASSIGNED

    def mark_picking_up(self):
        """Mark the rider as en route to the restaurant."""
        self.status = self.STATUS_PICKING_UP

    def mark_delivering(self):
        """Record pickup and mark the rider as en route to the customer."""
        self.pickup_time = globalvar.get_value("tick", 0)
        self.status = self.STATUS_DELIVERING

    def complete(self, tick, rider_id=None):
        """Finish the order and compute delivery statistics.

        Args:
            tick: Simulated tick at which delivery happened.
            rider_id: Optional rider identifier to store.
        """
        if rider_id is not None:
            self.rider_id = rider_id
        self.status = self.STATUS_COMPLETED
        self.completion_time = tick
        self.time_taken = max(0, tick - self.start_time)
        self.efficiency = (round(self.distance / self.time_taken, 2)
                           if self.time_taken > 0 else None)

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "efficiency": self.efficiency,
        }

    def __repr__(self):
        return f"Order(id={self.id}, status={self.status}, rider={self.rider_id})"
