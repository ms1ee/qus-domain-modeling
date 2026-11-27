"""Order data model."""

import globalvar
from path_planner import planner


def _validate_pos(pos, name):
    """Validate and convert a position to an integer tuple."""
    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
        raise ValueError("%s must be a pair of coordinates" % name)
    try:
        return (int(pos[0]), int(pos[1]))
    except (TypeError, ValueError):
        raise ValueError("%s coordinates must be integers" % name)


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are converted to grid cell centres on creation.

    Status lifecycle: ``pending`` -> ``assigned`` -> ``picking_up`` ->
    ``delivering`` -> ``completed``.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order.

        :param res_pos: restaurant (x, y) in 0-800.
        :param cus_pos: customer (x, y) in 0-800.
        """
        rp = _validate_pos(res_pos, "restaurant")
        cp = _validate_pos(cus_pos, "customer")
        self.raw = [rp[0], rp[1], cp[0], cp[1]]
        self.res_pos = planner.to_grid_center(*rp)
        self.cus_pos = planner.to_grid_center(*cp)
        counter = (globalvar.get_value("order_counter") or 0) + 1
        globalvar.set_value("order_counter", counter)
        self.id = counter
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.current_time()
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.time_taken = None
        self.distance = planner.manhattan(self.res_pos, self.cus_pos)
        self.travel_distance = None
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(self)

    def assign_to(self, rider_id):
        """Record that this order is assigned to rider ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assign_time = globalvar.current_time()

    def to_list(self):
        """Return ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.res_pos[0], self.res_pos[1],
                self.cus_pos[0], self.cus_pos[1]]

    @property
    def efficiency(self):
        """Delivery efficiency: order distance per tick (None if unknown)."""
        if self.time_taken:
            return round(self.distance / self.time_taken, 2)
        return None

    def to_dict(self):
        """Serialisable representation."""
        return {
            "id": self.id,
            "raw": self.raw,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "travel_distance": self.travel_distance,
        }

    def __repr__(self):
        return "Order(id=%s, %s->%s, %s)" % (self.id, self.res_pos,
                                             self.cus_pos, self.status)
