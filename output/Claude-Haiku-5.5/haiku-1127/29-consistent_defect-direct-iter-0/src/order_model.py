"""Order data model.

An order travels through the statuses:
    pending -> assigned -> picking_up -> delivering -> completed
"""

import globalvar
from path_planner import PathPlanner

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _next_order_id():
    """Issue the next unique order id.

    Returns:
        int: Monotonically increasing order id starting at 1.
    """
    counter = globalvar.get_value("order_id_counter", 0) + 1
    globalvar.set_value("order_id_counter", counter)
    return counter


class Order:
    """A single food delivery order.

    Attributes:
        id (int): Unique order identifier.
        res_pos (tuple[int, int]): Restaurant grid point (snapped).
        cus_pos (tuple[int, int]): Customer grid point (snapped).
        status (str): Lifecycle status (see module constants).
        rider_id (int | None): Assigned rider id.
        start_time (int): Tick when the order was created.
        completion_time (int | None): Tick when delivery finished.
        time_taken (int | None): Ticks between creation and completion.
        distance (int): Manhattan distance restaurant -> customer.
        efficiency (float | None): distance / time_taken after completion.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order and snap its coordinates to grid cell corners.

        Args:
            res_pos: Restaurant ``(x, y)``.
            cus_pos: Customer ``(x, y)``.
        """
        self.id = _next_order_id()
        self.res_pos = PathPlanner.snap_point(res_pos)
        self.cus_pos = PathPlanner.snap_point(cus_pos)
        self.status = STATUS_PENDING
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0)
        self.completion_time = None
        self.time_taken = None
        self.distance = PathPlanner.manhattan(self.res_pos, self.cus_pos)
        self.efficiency = None

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider.

        The caller is responsible for appending the order to the rider's
        ``orders`` list.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def complete(self, tick):
        """Mark the order completed and record timing and efficiency.

        Args:
            tick: Current simulation tick at delivery.
        """
        self.status = STATUS_COMPLETED
        self.completion_time = tick
        self.time_taken = max(0, tick - self.start_time)
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 3)
        else:
            self.efficiency = float(self.distance)

    def to_dict(self):
        """Serialize the order to a JSON-compatible dict.

        Returns:
            dict: Order attributes.
        """
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
            "efficiency": self.efficiency,
        }
