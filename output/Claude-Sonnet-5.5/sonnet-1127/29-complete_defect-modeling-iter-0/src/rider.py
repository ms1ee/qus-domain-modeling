"""Rider model."""
import globalvar
from pathplanner import PathPlanner


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 0
        self.y = 0
        self.speed = 10
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self.planner = PathPlanner()
        self._record("spawn", None)

    @property
    def pos(self):
        return (self.x, self.y)

    def _record(self, event, order_id):
        self.log.append({
            "event": event, "order_id": order_id,
            "time": globalvar.get_value("tick", 0) or 0,
            "x": self.x, "y": self.y, "state": self.state,
        })

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self.orders:
                return
            self.state = 1
            self._record("accepted_order", self.orders[0].id)
            return
        order = self.orders[0]
        target = order.res_pos if self.state == 1 else order.cus_pos
        if self.pos != target:
            self.x, self.y = self.planner.next_position(
                self.pos, target, self.speed)
        if self.pos == target:
            if self.state == 1:
                self.state = 2
                self._record("arrived_at_merchant", order.id)
            else:
                order.complete(globalvar.get_value("tick", 0) or 0)
                self.state = 0
                self.orders.pop(0)
                self._record("delivered_to_customer", order.id)
