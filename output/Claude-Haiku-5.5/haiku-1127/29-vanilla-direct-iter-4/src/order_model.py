"""Order data model: input validation, grid conversion and order records."""

import globalvar

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = 8

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def validate_coordinate(value, label="coordinate"):
    """Validate that a value is an integer within the map range.

    Args:
        value: Value to check.
        label: Name used in error messages.

    Returns:
        The validated integer.

    Raises:
        TypeError: If the value is not an integer.
        ValueError: If the value is outside 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer, got {value!r}")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(f"{label} {value} is outside the range 0-{MAP_SIZE}")
    return value


def validate_order_coordinates(coords):
    """Validate the four-element order input ``[rx, ry, cx, cy]``.

    Args:
        coords: Sequence of four values.

    Returns:
        Tuple of four validated integers.

    Raises:
        ValueError: If the length is wrong or a value is out of range.
        TypeError: If a value is not an integer.
    """
    values = list(coords)
    if len(values) != 4:
        raise ValueError("an order needs exactly 4 coordinates: "
                         "restaurant_x restaurant_y customer_x customer_y")
    labels = ("restaurant x", "restaurant y", "customer x", "customer y")
    return tuple(validate_coordinate(v, lbl) for v, lbl in zip(values, labels))


def cell_index(value):
    """Return the grid cell index (0-7) containing a coordinate.

    Args:
        value: Validated coordinate in 0-800.

    Returns:
        Cell index; 800 maps to the last cell (7).
    """
    return min(value // CELL_SIZE, GRID_CELLS - 1)


def cell_center(value):
    """Convert a coordinate to the centre of its grid cell.

    Implements ``center = (grid // 100) * 100 + 50``; the boundary value 800
    is attributed to the last cell so the centre stays on the map.

    Args:
        value: Validated coordinate in 0-800.

    Returns:
        Integer cell-centre coordinate.
    """
    return cell_index(validate_coordinate(value)) * CELL_SIZE + CELL_SIZE // 2


def _next_order_id():
    """Issue the next unique order id from the global counter."""
    order_id = globalvar.get_value("order_counter", 0) + 1
    globalvar.set_value("order_counter", order_id)
    return order_id


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        raw_res_pos: Restaurant coordinates as entered by the user.
        raw_cus_pos: Customer coordinates as entered by the user.
        res_pos: Restaurant grid-cell centre ``(x, y)``.
        cus_pos: Customer grid-cell centre ``(x, y)``.
        status: One of pending, assigned, picking_up, delivering, completed.
        rider_id: Assigned rider id or None.
        start_time: Tick at which the order was created.
        accept_time: Tick at which the rider started the pickup.
        pickup_time: Tick at which the rider reached the restaurant.
        complete_time: Tick at which the order was delivered.
        distance: Restaurant-to-customer route length in units.
        time_taken: Ticks from creation to delivery.
        efficiency: Distance per tick (units/tick) for completed orders.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order and convert its coordinates to cell centres.

        Args:
            res_pos: ``[x, y]`` restaurant coordinates (0-800).
            cus_pos: ``[x, y]`` customer coordinates (0-800).

        Raises:
            ValueError: If the coordinates are malformed or out of range.
            TypeError: If a coordinate is not an integer.
        """
        res = list(res_pos)
        cus = list(cus_pos)
        if len(res) != 2 or len(cus) != 2:
            raise ValueError("positions must be [x, y] pairs")
        self.raw_res_pos = (validate_coordinate(res[0], "restaurant x"),
                            validate_coordinate(res[1], "restaurant y"))
        self.raw_cus_pos = (validate_coordinate(cus[0], "customer x"),
                            validate_coordinate(cus[1], "customer y"))
        self.res_pos = (cell_center(self.raw_res_pos[0]),
                        cell_center(self.raw_res_pos[1]))
        self.cus_pos = (cell_center(self.raw_cus_pos[0]),
                        cell_center(self.raw_cus_pos[1]))
        self.id = _next_order_id()
        self.status = STATUS_PENDING
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0)
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.distance = 0
        self.time_taken = None
        self.efficiency = None

    def assign_to(self, rider_id):
        """Record that the order has been assigned to a rider.

        The caller is responsible for appending the order to the rider's
        ``orders`` list.

        Args:
            rider_id: Identifier of the assigned rider.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def complete(self, now):
        """Mark the order as delivered and compute efficiency data.

        Args:
            now: Current tick at delivery.
        """
        self.status = STATUS_COMPLETED
        self.complete_time = now
        self.time_taken = max(now - self.start_time, 0)
        self.efficiency = round(self.distance / max(self.time_taken, 1), 2)

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "status": self.status,
            "rider_id": self.rider_id,
            "restaurant_input": list(self.raw_res_pos),
            "customer_input": list(self.raw_cus_pos),
            "restaurant_center": list(self.res_pos),
            "customer_center": list(self.cus_pos),
            "start_time": self.start_time,
            "accept_time": self.accept_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
