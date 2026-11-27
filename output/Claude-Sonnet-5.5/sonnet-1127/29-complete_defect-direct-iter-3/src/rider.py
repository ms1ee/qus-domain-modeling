"""Rider model."""
from src import globalvar
from src.path_planner import PathPlanner


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 0
        self.y = 0
        self.speed = 50
        self.state = 0
        self.orders = []
        self.special_case = False
        self.path = []
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0),
                         "x": self.x, "y": self.y})

    def _set_path(self, target):
        self.path = PathPlanner.plan((self.x, self.y), target)

    def _advance(self):
        budget = self.speed
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = abs(dx) + abs(dy)
            if dist == 0:
                self.path.pop(0)
                continue
            step = min(budget, dist)
            if dx:
                self.x += step if dx > 0 else -step
            else:
                self.y += step if dy > 0 else -step
            budget -= step
            if step == dist:
                self.path.pop(0)

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self.orders:
                return
            order = self.orders[0]
            self.state = 1
            order.status = "picking_up"
            self._log("accepted_order", order.id)
            self._set_path(order.res_pos)
        if not self.orders:
            self.state = 0
            return
        order = self.orders[0]
        self._advance()
        if self.state == 1 and not self.path and \
                (self.x, self.y) == tuple(order.res_pos):
            self.state = 2
            order.status = "delivering"
            self._log("arrived_at_merchant", order.id)
            self._set_path(order.cus_pos)
        if self.state == 2 and not self.path and \
                (self.x, self.y) == tuple(order.cus_pos):
            order.complete()
            self._log("delivered_to_customer", order.id)
            self.orders.pop(0)
            self.state = 0
