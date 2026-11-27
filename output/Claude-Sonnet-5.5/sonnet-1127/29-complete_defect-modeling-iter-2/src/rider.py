"""Rider model and movement."""
import globalvar


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
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("tick", 0),
                         "x": self.x, "y": self.y})

    def _step_toward(self, tx, ty):
        """Move up to speed units: horizontal first, then vertical."""
        budget = self.speed
        dx = tx - self.x
        if dx and budget:
            s = min(abs(dx), budget)
            self.x += s if dx > 0 else -s
            budget -= s
        dy = ty - self.y
        if dy and budget:
            s = min(abs(dy), budget)
            self.y += s if dy > 0 else -s

    def move(self):
        """Advance one tick."""
        if self.state == 0 and self.orders:
            self.state = 1
            self._log("accepted_order", self.orders[0].id)
        if self.state == 0 or not self.orders:
            return
        order = self.orders[0]
        target = order.res_pos if self.state == 1 else order.cus_pos
        self._step_toward(*target)
        if (self.x, self.y) == tuple(target):
            if self.state == 1:
                self._log("arrived_at_merchant", order.id)
                self.state = 2
            else:
                order.status = "completed"
                order.completion_time = globalvar.get_value("tick", 0)
                self._log("delivered_to_customer", order.id)
                self.orders.pop(0)
                self.state = 0
