"""Order data model."""

import globalvar
from config import get_config
from path_planner import PathPlanner, MAP_SIZE

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _validate_pos(pos, name):
    try:
        x, y = pos
    except (TypeError, ValueError):
        raise ValueError("%s must be a pair of coordinates" % name)
    for v in (x, y):
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("%s coordinates must be integers" % name)
        if v < 0 or v > MAP_SIZE:
            raise ValueError("%s coordinates must be in range 0-%d" % (name, MAP_SIZE))
    return (x, y)


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are converted to grid cell centres on creation.
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        raw_res = _validate_pos(res_pos, "Restaurant")
        raw_cus = _validate_pos(cus_pos, "Customer")
        self.id = Order._next_id
        Order._next_id += 1
        self.raw_res_pos = raw_res
        self.raw_cus_pos = raw_cus
        self.res_pos = PathPlanner.to_grid_center(*raw_res)
        self.cus_pos = PathPlanner.to_grid_center(*raw_cus)
        self.res_grid = PathPlanner.grid_index(*self.res_pos)
        self.cus_grid = PathPlanner.grid_index(*self.cus_pos)
        self.status = STATUS_PENDING
        self.rider_id = None
        self.create_time = globalvar.get_value("time", 0)
        self.assign_time = None
        self.accept_time = None
        self.pickup_time = None
        self.complete_time = None
        self.time_taken = None
        self.distance = PathPlanner.path_length(
            self.res_pos, PathPlanner.plan_path(self.res_pos, self.cus_pos))
        cfg = get_config()
        self.fee = int(cfg.get("base_fee", 30)) + \
            (self.distance // 100) * int(cfg.get("fee_per_100", 5))

    def assign_to(self, rider_id):
        """Mark this order as assigned to the given rider."""
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED
        self.assign_time = globalvar.get_value("time", 0)

    def mark_accepted(self, now):
        """Rider started heading to the restaurant."""
        self.status = STATUS_PICKING_UP
        self.accept_time = now

    def mark_picked_up(self, now):
        """Rider arrived at the restaurant and picked up the food."""
        self.status = STATUS_DELIVERING
        self.pickup_time = now

    def complete(self, now, rider_id=None):
        """Mark the order as delivered."""
        self.status = STATUS_COMPLETED
        self.complete_time = now
        if rider_id is not None:
            self.rider_id = rider_id
        self.time_taken = max(0, now - self.create_time)

    def to_dict(self):
        """Serialisable representation."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "raw_res_pos": list(self.raw_res_pos),
            "raw_cus_pos": list(self.raw_cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "create_time": self.create_time,
            "assign_time": self.assign_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "fee": self.fee,
        }

    def __repr__(self):
        return "Order(id=%d, res=%s, cus=%s, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)


def reset_order_counter():
    """Reset the order id counter (used on system initialisation)."""
    Order._next_id = 1
