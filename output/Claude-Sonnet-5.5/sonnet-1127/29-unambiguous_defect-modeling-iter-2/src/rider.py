"""Rider class."""
import globalvar
from pathplanner import PathPlanner


class Rider:
    """A delivery rider. state: 0 idle, 1 picking up, 2 delivering."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 0
        self.y = (rider_id % 8) * 100  # on a road (x is a grid line)
        self.speed = 50
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._log("spawn", None)

    @property
    def pos(self):
        return (self.x, self.y)

    def _log(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("tick") or 0,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def move(self):
        """Advance one tick."""
        budget = self.speed
        if self.state == 0:
            if not self.orders:
                return
            self.state = 1
            self._log("accepted_order", self.orders[0].id)
        for _ in range(4):
            if not self.orders:
                self.state = 0
                return
            order = self.orders[0]
            target = order.res_pos if self.state == 1 else order.cus_pos
            if self.pos != target:
                if budget <= 0:
                    return
                before = self.pos
                self.x, self.y = PathPlanner.step(self.pos, target, budget)
                budget -= PathPlanner.distance(before, self.pos)
            if self.pos == target:
                if self.state == 1:
                    self.state = 2
                    self._log("arrived_at_merchant", order.id)
                else:
                    order.complete(globalvar.get_value("tick") or 0)
                    self.orders.pop(0)
                    self.state = 0
                    self._log("delivered_to_customer", order.id)
                    return
            else:
                return
