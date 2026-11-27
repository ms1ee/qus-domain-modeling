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
        self.log = []
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("tick", 0),
                         "x": self.x, "y": self.y, "state": self.state})

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self.orders:
                return
            self.state = 1
            self._record("accepted_order", self.orders[0].id)
        order = self.orders[0] if self.orders else None
        if order is None:
            self.state = 0
            return
        if self.state == 1:
            tx, ty = order.res_pos
            self._advance(tx, ty)
            if (self.x, self.y) == (tx, ty):
                self.state = 2
                self._record("arrived_at_merchant", order.id)
        elif self.state == 2:
            tx, ty = order.cus_pos
            self._advance(tx, ty)
            if (self.x, self.y) == (tx, ty):
                order.complete(globalvar.get_value("tick", 0))
                self.orders.pop(0)
                self.state = 0
                self.special_case = False
                self._record("delivered_to_customer", order.id)

    def _advance(self, tx, ty):
        # directly above/below the target: only vertical movement
        self.special_case = (self.x == tx and self.y != ty)
        self.x, self.y = _planner.step(self.x, self.y, tx, ty, self.speed)

    def to_dict(self):
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": self.state,
                "orders": [o.id for o in self.orders],
                "special_case": self.special_case}
