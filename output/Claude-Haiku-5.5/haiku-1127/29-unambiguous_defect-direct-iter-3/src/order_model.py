"""Order data model.

An order is defined by a restaurant location and a customer location. Both
inputs are transformed to grid cell centers, and each is served from the
street intersection of its cell (the access node).
"""

import itertools

import globalvar
import grid

STATUS_CREATED = "created"
STATUS_ASSIGNED = "assigned"
STATUS_PICKED_UP = "picked_up"
STATUS_COMPLETED = "completed"


def _validate_point(point, label):
    """Validate an ``(x, y)`` pair of integer coordinates.

    Args:
        point: Sequence of two integers.
        label: Human-readable name used in error messages.

    Returns:
        tuple[int, int]: The validated point.

    Raises:
        ValueError: If the point is malformed or out of range.
    """
    if len(point) != 2:
        raise ValueError(f"{label} location must have exactly two coordinates")
    x, y = point
    for value in (x, y):
        if not grid.is_valid_coordinate(value):
            raise ValueError(
                f"{label} coordinate {value!r} must be an integer in "
                f"[{grid.config.COORD_MIN}, {grid.config.COORD_MAX}]"
            )
    return x, y


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier (auto-incremented).
        res_input: Raw restaurant coordinates as entered.
        cus_input: Raw customer coordinates as entered.
        res_pos: Restaurant grid cell center ``(x, y)``.
        cus_pos: Customer grid cell center ``(x, y)``.
        restaurant_node: Street intersection used for pickup.
        customer_node: Street intersection used for delivery.
        distance: Manhattan distance from restaurant to customer node.
        status: One of created, assigned, picked_up, completed.
        rider_id: ID of the assigned rider, or None.
        created_tick, start_tick, pickup_tick, complete_tick: Timing data.
    """

    _id_sequence = itertools.count(1)

    def __init__(self, res_pos, cus_pos):
        """Create an order from raw restaurant and customer coordinates.

        Args:
            res_pos: ``(x, y)`` restaurant location, integers in 0-800.
            cus_pos: ``(x, y)`` customer location, integers in 0-800.

        Raises:
            ValueError: If either location is malformed or out of range.
        """
        res_pos = _validate_point(res_pos, "Restaurant")
        cus_pos = _validate_point(cus_pos, "Customer")

        self.id = next(Order._id_sequence)
        self.res_input = res_pos
        self.cus_input = cus_pos
        self.res_pos = grid.snap_to_center(*res_pos)
        self.cus_pos = grid.snap_to_center(*cus_pos)
        self.restaurant_node = grid.access_node(self.res_pos)
        self.customer_node = grid.access_node(self.cus_pos)
        self.distance = grid.manhattan(self.restaurant_node, self.customer_node)

        self.status = STATUS_CREATED
        self.rider_id = None
        self.created_tick = globalvar.get_value("tick", 0)
        self.start_tick = None
        self.pickup_tick = None
        self.complete_tick = None

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider.

        The caller is responsible for appending the order to the rider's
        ``orders`` list.

        Args:
            rider_id: ID of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED
        self.start_tick = globalvar.get_value("tick", 0)

    def mark_picked_up(self, tick):
        """Record that the rider collected the food at the restaurant.

        Args:
            tick: Simulation tick of the pickup.
        """
        self.status = STATUS_PICKED_UP
        self.pickup_tick = tick

    def mark_completed(self, tick):
        """Record delivery completion.

        Args:
            tick: Simulation tick of the delivery.
        """
        self.status = STATUS_COMPLETED
        self.complete_tick = tick

    @property
    def time_taken(self):
        """Ticks from assignment to completion, or None if not completed."""
        if self.start_tick is None or self.complete_tick is None:
            return None
        return self.complete_tick - self.start_tick

    @property
    def efficiency(self):
        """Delivery efficiency in distance units per tick, or None."""
        taken = self.time_taken
        if not taken:
            return None
        return self.distance / taken

    def to_dict(self):
        """Return a JSON-serializable representation of the order.

        Returns:
            dict: Order attributes.
        """
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "distance": self.distance,
            "status": self.status,
            "rider_id": self.rider_id,
            "created_tick": self.created_tick,
            "start_tick": self.start_tick,
            "pickup_tick": self.pickup_tick,
            "complete_tick": self.complete_tick,
            "time_taken": self.time_taken,
        }

    def __repr__(self):
        return (
            f"Order(id={self.id}, status={self.status!r}, "
            f"rider_id={self.rider_id})"
        )
