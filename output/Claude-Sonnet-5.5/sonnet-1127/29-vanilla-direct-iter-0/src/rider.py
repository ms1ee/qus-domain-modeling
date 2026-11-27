"""Rider model."""

import globalvar
from path_planner import PathPlanner


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
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0) or 0,
                         "x": self.x, "y": self.y})

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self.orders:
                return
            self.state = 1
            self._log("accepted_order", self.orders[0].id)
        order = self.orders[0] if self.orders else None
        if order is None:
            self.state = 0
            return
        if self.state == 1:
            tx, ty = order.res_pos
            self.x, self.y = PathPlanner.next_position(
                self.x, self.y, tx, ty, self.speed)
            if (self.x, self.y) == (tx, ty):
                self.state = 2
                self._log("arrived_at_merchant", order.id)
        elif self.state == 2:
            tx, ty = order.cus_pos
            self.x, self.y = PathPlanner.next_position(
                self.x, self.y, tx, ty, self.speed)
            if (self.x, self.y) == (tx, ty):
                order.complete()
                self.orders.pop(0)
                self.state = 0
                self._log("delivered_to_customer", order.id)

    def to_dict(self):
        """Serialise."""
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": self.state,
                "orders": [o.id for o in self.orders],
                "special_case": self.special_case}
