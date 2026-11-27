"""Order data model.

An order is created from user input ``[restaurant_x, restaurant_y,
customer_x, customer_y]`` (integers 0-800). The raw coordinates are kept for
reporting, and the locations are converted to grid cell centers for routing.
"""

import globalvar
from path_planner import MAP_SIZE, cell_center_coord, manhattan

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def validate_coordinate(value, label="coordinate"):
    """Validate that a value is an integer in the map range.

    Args:
        value: Value to validate.
        label: Name used in error messages.

    Returns:
        The validated integer.

    Raises:
        TypeError: If the value is not an integer.
        ValueError: If the value is outside 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"{label} {value} is outside the range 0-{MAP_SIZE}")
    return value


def _validate_position(pos, label):
    """Validate an ``(x, y)`` pair."""
    if len(pos) != 2:
        raise ValueError(f"{label} position must contain exactly 2 values")
    return (
        validate_coordinate(pos[0], f"{label} x"),
        validate_coordinate(pos[1], f"{label} y"),
    )


def _current_tick():
    """Return the current simulated tick."""
    return int(globalvar.get_value("current_tick") or 0)


def _next_order_id():
    """Issue the next unique order ID."""
    value = int(globalvar.get_value("order_id_counter") or 0) + 1
    globalvar.set_value("order_id_counter", value)
    return value


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        status: One of pending, assigned, picking_up, delivering, completed.
        restaurant_raw: Raw restaurant input ``(x, y)``.
        customer_raw: Raw customer input ``(x, y)``.
        restaurant_x / restaurant_y: Restaurant grid cell center.
        customer_x / customer_y: Customer grid cell center.
        start_time: Tick at which the order was created.
        completion_time: Tick at which the order was delivered, or None.
        distance: Restaurant-to-customer distance in map units.
        time_taken: Ticks from creation to completion, or None.
        rider_id: ID of the assigned rider, or None.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order from raw restaurant and customer coordinates.

        Args:
            res_pos: Restaurant position ``(x, y)`` with values 0-800.
            cus_pos: Customer position ``(x, y)`` with values 0-800.

        Raises:
            TypeError: If a coordinate is not an integer.
            ValueError: If a coordinate is out of range.
        """
        rx, ry = _validate_position(res_pos, "restaurant")
        cx, cy = _validate_position(cus_pos, "customer")
        self.id = _next_order_id()
        self.restaurant_raw = (rx, ry)
        self.customer_raw = (cx, cy)
        self.restaurant_x = cell_center_coord(rx)
        self.restaurant_y = cell_center_coord(ry)
        self.customer_x = cell_center_coord(cx)
        self.customer_y = cell_center_coord(cy)
        self.start_time = _current_tick()
        self.completion_time = None
        self.distance = 0
        self.time_taken = None
        self.rider_id = None
        self.status = STATUS_PENDING

    @property
    def restaurant_pos(self):
        """Return the restaurant cell center as ``(x, y)``."""
        return self.restaurant_x, self.restaurant_y

    @property
    def customer_pos(self):
        """Return the customer cell center as ``(x, y)``."""
        return self.customer_x, self.customer_y

    def assign_to(self, rider_id):
        """Record the rider this order is assigned to.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        if self.status == STATUS_PENDING:
            self.status = STATUS_ASSIGNED

    def complete(self, tick):
        """Mark the order as delivered and compute efficiency data.

        Args:
            tick: Simulated tick of delivery.

        Returns:
            Net income in funds: delivery fee minus a distance-based fuel cost.
        """
        self.status = STATUS_COMPLETED
        self.completion_time = tick
        self.distance = manhattan(self.restaurant_pos, self.customer_pos)
        self.time_taken = tick - self.start_time
        config = globalvar.get_value("config") or {}
        fee = int(config.get("order_fee", 100))
        divisor = int(config.get("fuel_divisor", 20)) or 1
        return fee - self.distance // divisor

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "status": self.status,
            "restaurant_raw": list(self.restaurant_raw),
            "customer_raw": list(self.customer_raw),
            "restaurant": list(self.restaurant_pos),
            "customer": list(self.customer_pos),
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "rider_id": self.rider_id,
        }
