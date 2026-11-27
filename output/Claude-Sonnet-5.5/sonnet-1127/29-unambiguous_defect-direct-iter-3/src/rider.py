"""Rider model."""
import globalvar
from pathplanner import PathPlanner


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 0
        self.y = (rider_id * 100) % 800
        self.speed = 50
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0),
                         "pos": (self.x, self.y)})

    def move(self):
        """Advance one tick."""
        if not self.orders:
            self.state = 0
            return
        order = self.orders[0]
        if self.state == 0:
            self.state = 1
            order.assign_to(self.rider_id)
            self._record("accepted_order", order.id)
        if self.state == 1:
            tx, ty = order.res_pos
            self.x, self.y = PathPlanner.step(self.x, self.y, tx, ty,
                                              self.speed)
            if (self.x, self.y) == (tx, ty):
                self.state = 2
                self._record("arrived_at_merchant", order.id)
        elif self.state == 2:
            tx, ty = order.cus_pos
            self.x, self.y = PathPlanner.step(self.x, self.y, tx, ty,
                                              self.speed)
            if (self.x, self.y) == (tx, ty):
                order.status = "completed"
                order.end_time = globalvar.get_value("time", 0)
                self.orders.pop(0)
                self.state = 0
                self._record("delivered_to_customer", order.id)
