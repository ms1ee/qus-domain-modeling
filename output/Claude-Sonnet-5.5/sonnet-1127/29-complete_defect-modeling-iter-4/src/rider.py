"""Rider model."""

try:
    from src import globalvar
    from src.path_planner import PathPlanner
except ImportError:  # pragma: no cover
    import globalvar
    from path_planner import PathPlanner

IDLE, PICKING, DELIVERING = 0, 1, 2


class Rider:
    """A delivery rider moving on the grid."""

    def __init__(self, rider_id, speed=50):
        self.rider_id = rider_id
        self.x = 0
        self.y = 0
        self.speed = speed
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.planner = PathPlanner()
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("tick", 0),
                         "x": self.x, "y": self.y, "state": self.state})

    def move(self):
        """Advance one tick; handle state transitions and logging."""
        if self.state == IDLE:
            if not self.orders:
                return
            self.state = PICKING
            self._log("accepted_order", self.orders[0].id)
            if self.orders[0].status == "assigned":
                self.orders[0].status = "picking_up"
        order = self.orders[0]
        target = order.res_pos if self.state == PICKING else order.cus_pos
        self.x, self.y = self.planner.step((self.x, self.y), target,
                                           self.speed)
        if (self.x, self.y) != tuple(target):
            return
        if self.state == PICKING:
            self.state = DELIVERING
            order.status = "delivering"
            self._log("arrived_at_merchant", order.id)
        else:
            now = globalvar.get_value("tick", 0)
            order.status = "completed"
            order.completion_time = now
            order.time_taken = max(0, now - order.start_time)
            order.efficiency = (order.distance / order.time_taken
                                if order.time_taken else float(order.distance))
            self.orders.pop(0)
            self.state = IDLE
            self._log("delivered_to_customer", order.id)
