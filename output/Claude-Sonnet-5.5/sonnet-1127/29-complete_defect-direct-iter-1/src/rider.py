"""Rider model."""

import globalvar
from path_planner import PathPlanner


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id, x=50, y=50, speed=50):
        self.rider_id = rider_id
        self.x = x
        self.y = y
        self.speed = speed
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0) or 0,
                         "x": self.x, "y": self.y})

    @property
    def pos(self):
        return (self.x, self.y)

    def move(self):
        """Advance one tick, handling state transitions."""
        if self.state == 0:
            if not self.orders:
                return
            self.state = 1
            self._record("accepted_order", self.orders[0].id)
        order = self.orders[0]
        target = order.res_pos if self.state == 1 else order.cus_pos
        # special case: aligned on a vertical/horizontal line with target
        self.special_case = (self.x == target[0] or self.y == target[1])
        self.x, self.y = PathPlanner.step(self.pos, target, self.speed)
        if self.pos != tuple(target):
            return
        if self.state == 1:
            self._record("arrived_at_merchant", order.id)
            self.state = 2
        else:
            now = globalvar.get_value("time", 0) or 0
            order.complete(now)
            self._record("delivered_to_customer", order.id)
            self.orders.pop(0)
            self.state = 0
            self.special_case = False
