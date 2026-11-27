"""Rider model."""

import globalvar
from pathplanner import PathPlanner

_planner = PathPlanner()


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
        self.path = []
        self.log = []
        self._log("spawn", None)

    @property
    def id(self):
        return self.rider_id

    def _log(self, event, order_id):
        self.log.append({
            "time": globalvar.get_value("tick", 0) or 0,
            "x": self.x,
            "y": self.y,
            "event": event,
            "order_id": order_id,
        })

    def _plan_to(self, target):
        self.path = _planner.plan((self.x, self.y), target)
        # Special case: already aligned with target on one axis.
        self.special_case = len(self.path) == 1

    def _follow(self):
        budget = self.speed
        while budget > 0 and self.path:
            wx, wy = self.path[0]
            dist = abs(wx - self.x) + abs(wy - self.y)
            if dist <= budget:
                self.x, self.y = wx, wy
                budget -= dist
                self.path.pop(0)
            else:
                if wx != self.x:
                    self.x += budget if wx > self.x else -budget
                else:
                    self.y += budget if wy > self.y else -budget
                budget = 0

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self.orders:
                return
            order = self.orders[0]
            self.state = 1
            self._log("accepted_order", order.id)
            self._plan_to(tuple(order.res_pos))
        if self.state == 1:
            order = self.orders[0]
            self._follow()
            if (self.x, self.y) == tuple(order.res_pos):
                self.state = 2
                self._log("arrived_at_merchant", order.id)
                self._plan_to(tuple(order.cus_pos))
            return
        if self.state == 2:
            order = self.orders[0]
            self._follow()
            if (self.x, self.y) == tuple(order.cus_pos):
                now = globalvar.get_value("tick", 0) or 0
                order.status = "completed"
                order.completion_time = now
                order.time_taken = now - order.start_time
                self.orders.pop(0)
                self._log("delivered_to_customer", order.id)
                self.path = []
                self.special_case = False
                self.state = 0

    def to_dict(self):
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": self.state,
                "orders": [o.id for o in self.orders],
                "special_case": self.special_case}
