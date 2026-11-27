"""Rider model."""
import globalvar
from path_planner import PathPlanner


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 50
        self.y = 50
        self.speed = 50
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("tick", 0),
                         "x": self.x, "y": self.y})

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self.orders:
                return
            self.state = 1
            self._log("accepted_order", self.orders[0].id)
        order = self.orders[0]
        if self.state == 1:
            tx, ty = order.res_pos
            self.x, self.y = PathPlanner.step(self.x, self.y, tx, ty, self.speed)
            if (self.x, self.y) == (tx, ty):
                self.state = 2
                self._log("arrived_at_merchant", order.id)
        elif self.state == 2:
            tx, ty = order.cus_pos
            self.x, self.y = PathPlanner.step(self.x, self.y, tx, ty, self.speed)
            if (self.x, self.y) == (tx, ty):
                order.status = "completed"
                order.complete_time = globalvar.get_value("tick", 0)
                self.orders.pop(0)
                self.state = 0
                self._log("delivered_to_customer", order.id)
