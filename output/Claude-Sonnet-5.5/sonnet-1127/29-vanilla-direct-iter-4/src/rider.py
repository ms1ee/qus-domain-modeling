"""Rider class."""
import globalvar
from pathplanner import PathPlanner


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 435
        self.y = 385
        self.speed = 10
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("time", 0),
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "rider_id": self.rider_id,
        })

    def _target(self):
        o = self.orders[0]
        return o.res_pos if self.state == 1 else o.cus_pos

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self.orders:
                return
            self.state = 1
            self._record("accepted_order", self.orders[0].id)
        if not self.orders:
            self.state = 0
            return
        tx, ty = self._target()
        self.x, self.y = PathPlanner.next_point(
            self.x, self.y, tx, ty, self.speed)
        if (self.x, self.y) == (tx, ty):
            order = self.orders[0]
            if self.state == 1:
                self._record("arrived_at_merchant", order.id)
                self.state = 2
                order.status = "delivering"
            else:
                self.orders.pop(0)
                order.complete(globalvar.get_value("time", 0))
                self.state = 0
                self._record("delivered_to_customer", order.id)
                if self.orders:
                    self.state = 1
                    self._record("accepted_order", self.orders[0].id)
