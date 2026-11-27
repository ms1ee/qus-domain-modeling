"""Order data model: a single delivery request and its lifecycle."""

import globalvar
import grid

PENDING = "pending"
ASSIGNED = "assigned"
PICKING_UP = "picking_up"
DELIVERING = "delivering"
COMPLETED = "completed"


def _next_order_id():
    """Return the next unique order ID and advance the global counter."""
    value = int(globalvar.get_value("order_counter", 0)) + 1
    globalvar.set_value("order_counter", value)
    return value


def _now():
    """Return the current simulated time."""
    return int(globalvar.get_value("time", 0))


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique positive integer identifier.
        raw_input: The four user-entered coordinates
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.
        res_pos: Restaurant location snapped to a grid intersection.
        cus_pos: Customer location snapped to a grid intersection.
        status: One of "pending", "assigned", "picking_up", "delivering",
            "completed".
        rider_id: ID of the assigned rider, or None.
        created_time: Simulated time when the order was created.
        assigned_time: Simulated time of assignment.
        accepted_time: Simulated time the rider started pickup.
        pickup_time: Simulated time the rider reached the restaurant.
        complete_time: Simulated time the order was delivered.
        distance: Manhattan distance from restaurant to customer.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: Pair ``(x, y)`` of the restaurant location (0-800).
            cus_pos: Pair ``(x, y)`` of the customer location (0-800).

        Raises:
            ValueError: If a location is malformed or out of range.
        """
        res = self._parse_point(res_pos, "restaurant")
        cus = self._parse_point(cus_pos, "customer")
        self.id = _next_order_id()
        self.raw_input = list(res + cus)
        self.res_pos = grid.snap_to_grid(*res)
        self.cus_pos = grid.snap_to_grid(*cus)
        self.status = PENDING
        self.rider_id = None
        self.created_time = _now()
        self.assigned_time = None
        self.accepted_time = None
        self.pickup_time = None
        self.complete_time = None
        self.distance = grid.manhattan(self.res_pos, self.cus_pos)

    @staticmethod
    def _parse_point(point, label):
        """Validate a coordinate pair and return it as integers.

        Args:
            point: Pair of coordinates.
            label: Name used in error messages.

        Raises:
            ValueError: If the point is malformed or out of range.
        """
        try:
            x, y = point
        except (TypeError, ValueError):
            raise ValueError(f"{label} location must be an (x, y) pair")
        return grid.validate_coordinate(x), grid.validate_coordinate(y)

    def assign_to(self, rider_id):
        """Record that this order is assigned to the rider with ``rider_id``.

        Args:
            rider_id: The identifier of the assigned rider.
        """
        self.rider_id = rider_id
        self.status = ASSIGNED
        self.assigned_time = _now()

    def mark_accepted(self, now):
        """Mark that the rider has started the pickup leg.

        Args:
            now: Current simulated time.
        """
        self.status = PICKING_UP
        self.accepted_time = now

    def mark_picked_up(self, now):
        """Mark that the rider has arrived at the restaurant.

        Args:
            now: Current simulated time.
        """
        self.status = DELIVERING
        self.pickup_time = now

    def mark_completed(self, now):
        """Mark the order as delivered to the customer.

        Args:
            now: Current simulated time.
        """
        self.status = COMPLETED
        self.complete_time = now

    def time_taken(self):
        """Return ticks from creation to delivery, or None if unfinished."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.created_time

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "raw_input": self.raw_input,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_time": self.created_time,
            "assigned_time": self.assigned_time,
            "accepted_time": self.accepted_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
        }
