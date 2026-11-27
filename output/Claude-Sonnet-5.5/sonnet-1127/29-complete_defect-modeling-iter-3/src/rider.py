"""Rider model."""
import globalvar
from path_planner import PathPlanner


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 0
        self.y = 0
        self.speed = 100
        self.state = 0
        self.orders = []
        self.special_case = False
        self.planner = PathPlanner()
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0) or 0,
                         "x": self.x, "y": self.y})

    def _step(self, target):
        self.x, self.y = self.planner.next_step(
            self.x, self.y, target[0], target[1], self.speed)
        return (self.x, self.y) == tuple(target)

    def move(self):
        """Advance one tick."""
        if not self.orders:
            return
        order = self.orders[0]
        if self.state == 0:
            self.state = 1
            self._log("accepted_order", order.id)
            if order.status != "completed":
                order.status = "picking_up"
        if self.state == 1:
            if self._step(order.res_pos):
                self.state = 2
                order.status = "delivering"
                self._log("arrived_at_merchant", order.id)
        elif self.state == 2:
            if self._step(order.cus_pos):
                now = globalvar.get_value("time", 0) or 0
                order.status = "completed"
                order.completion_time = now
                order.time_taken = now - order.start_time
                self._log("delivered_to_customer", order.id)
                self.orders.pop(0)
                self.state = 0
                funds = globalvar.get_value("funds", 0) or 0
                globalvar.set_value("funds", funds + 100)
