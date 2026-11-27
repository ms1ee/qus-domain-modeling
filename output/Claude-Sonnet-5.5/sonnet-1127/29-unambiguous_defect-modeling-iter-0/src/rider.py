"""Rider model."""
import globalvar
from path_planner import PathPlanner

IDLE, PICKING, DELIVERING = 0, 1, 2


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 0
        self.y = (rider_id % 8) * 100 + 0  # on a street line
        self.speed = 50
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.path = None
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({
            "event": event, "order_id": order_id,
            "time": globalvar.get_value("tick", 0) or 0,
            "x": self.x, "y": self.y})

    def _step_towards(self, target):
        """Move up to speed units (x first, then y)."""
        budget = self.speed
        tx, ty = target
        dx = max(-budget, min(budget, tx - self.x))
        self.x += dx
        budget -= abs(dx)
        dy = max(-budget, min(budget, ty - self.y))
        self.y += dy

    def move(self):
        """Advance one tick."""
        if not self.orders:
            self.state = IDLE
            return
        order = self.orders[0]
        if self.state == IDLE:
            self.state = PICKING
            self.path = PathPlanner().plan(
                (self.x, self.y), tuple(order.res_pos), self.speed)
            self._log("accepted_order", order.id)
        if self.state == PICKING:
            self._step_towards(order.res_pos)
            if (self.x, self.y) == tuple(order.res_pos):
                self.state = DELIVERING
                self.path = PathPlanner().plan(
                    (self.x, self.y), tuple(order.cus_pos), self.speed)
                self._log("arrived_at_merchant", order.id)
            return
        if self.state == DELIVERING:
            self._step_towards(order.cus_pos)
            if (self.x, self.y) == tuple(order.cus_pos):
                self._log("delivered_to_customer", order.id)
                order.complete(globalvar.get_value("tick", 0) or 0)
                self.orders.pop(0)
                self.state = IDLE
                self.path = None

    def to_dict(self):
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": self.state,
                "orders": [o.id for o in self.orders],
                "special_case": self.special_case}
