"""Rider model."""
import globalvar
from pathplanner import PathPlanner

_planner = PathPlanner()


class Rider:
    """Delivery rider. state: 0 idle, 1 picking up, 2 delivering."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 400
        self.y = 400
        self.speed = 20
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"time": globalvar.get_value("tick", 0),
                         "event": event, "order_id": order_id,
                         "x": self.x, "y": self.y, "state": self.state})

    def active_order(self):
        for o in self.orders:
            if o.status != "completed":
                return o
        return None

    def pending_count(self):
        return sum(1 for o in self.orders if o.status != "completed")

    def move(self):
        """Advance one tick."""
        order = self.active_order()
        if order is None:
            self.state = 0
            return
        if self.state == 0:
            self.state = 1
            self._log("accepted_order", order.id)
        target = order.res_pos if self.state == 1 else order.cus_pos
        self.special_case = self.x % 100 != 0 and self.y % 100 != 0
        self.x, self.y = _planner.step((self.x, self.y), target, self.speed)
        if (self.x, self.y) != tuple(target):
            return
        if self.state == 1:
            self.state = 2
            self._log("arrived_at_merchant", order.id)
        else:
            order.complete(globalvar.get_value("tick", 0))
            self.state = 0
            self._log("delivered_to_customer", order.id)
            nxt = self.active_order()
            if nxt is not None:
                self.state = 1
                self._log("accepted_order", nxt.id)
