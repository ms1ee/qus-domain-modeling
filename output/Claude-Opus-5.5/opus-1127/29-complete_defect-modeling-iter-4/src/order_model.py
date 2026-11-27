"""Order data model."""

import globalvar
from path_planner import PathPlanner, to_grid_center, to_grid_index, MAP_SIZE

ORDER_PENDING = "pending"
ORDER_ASSIGNED = "assigned"
ORDER_PICKING_UP = "picking_up"
ORDER_DELIVERING = "delivering"
ORDER_COMPLETED = "completed"


def _validate_coordinate(value, label):
    """Validate a single coordinate and return it as int."""
    if isinstance(value, bool):
        raise ValueError("{} must be an integer".format(label))
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
        result = int(value.strip())
    elif isinstance(value, float) and value.is_integer():
        result = int(value)
    else:
        raise ValueError("{} must be an integer, got {!r}".format(label, value))
    if result < 0 or result > MAP_SIZE:
        raise ValueError("{} must be in range 0-{}, got {}".format(
            label, MAP_SIZE, result))
    return result


def _validate_pos(pos, label):
    """Validate a 2-element position."""
    try:
        items = list(pos)
    except TypeError:
        raise ValueError("{} position must be a pair of integers".format(label))
    if len(items) != 2:
        raise ValueError("{} position must have 2 coordinates".format(label))
    return (_validate_coordinate(items[0], label + " x"),
            _validate_coordinate(items[1], label + " y"))


class Order:
    """A delivery order from a restaurant to a customer."""

    def __init__(self, res_pos, cus_pos):
        rx, ry = _validate_pos(res_pos, "restaurant")
        cx, cy = _validate_pos(cus_pos, "customer")
        self.raw_restaurant = (rx, ry)
        self.raw_customer = (cx, cy)
        self.res_pos = (to_grid_center(rx), to_grid_center(ry))
        self.cus_pos = (to_grid_center(cx), to_grid_center(cy))
        counter = globalvar.get_value("order_id_counter", 0) or 0
        self.id = counter + 1
        globalvar.set_value("order_id_counter", self.id)
        self.start_time = globalvar.get_value("tick", 0) or 0
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.status = ORDER_PENDING
        self.rider_id = None
        self.distance = PathPlanner().plan(self.res_pos, self.cus_pos).length
        self.travel_distance = 0

    @property
    def restaurant_x(self):
        return self.res_pos[0]

    @property
    def restaurant_y(self):
        return self.res_pos[1]

    @property
    def customer_x(self):
        return self.cus_pos[0]

    @property
    def customer_y(self):
        return self.cus_pos[1]

    @property
    def restaurant_cell(self):
        return (to_grid_index(self.res_pos[0]), to_grid_index(self.res_pos[1]))

    @property
    def customer_cell(self):
        return (to_grid_index(self.cus_pos[0]), to_grid_index(self.cus_pos[1]))

    def assign_to(self, rider_id):
        """Assign the order to a rider."""
        self.rider_id = rider_id
        if self.status == ORDER_PENDING:
            self.status = ORDER_ASSIGNED

    def is_completed(self):
        return self.status == ORDER_COMPLETED

    def to_dict(self):
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "raw_restaurant": list(self.raw_restaurant),
            "raw_customer": list(self.raw_customer),
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "travel_distance": self.travel_distance,
            "status": self.status,
            "rider_id": self.rider_id,
        }

    def __repr__(self):
        return "Order(id={}, {}->{}, status={})".format(
            self.id, self.res_pos, self.cus_pos, self.status)
